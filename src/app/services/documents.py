from __future__ import annotations

import contextlib
import uuid
from typing import BinaryIO

from fastapi import UploadFile

from app.application.ports.unit_of_work import UnitOfWork
from app.core.config import get_settings
from app.domain.access_policy import Action
from app.domain.errors import (
    EmptyFilenameError,
    FileTooLarge,
    NoFilesProvidedError,
    ProjectNotFound,
    ProjectQuotaExceeded,
    StorageFileNotFound,
)
from app.models.document import Document
from app.services.access import require_document_access, require_project_access
from app.services.file_validation import (
    generate_safe_stored_filename,
    validate_file_upload,
)
from app.storage.base import StorageBackend
from app.storage.s3 import format_s3_key


def read_upload_file_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read upload file content in chunks up to max_bytes without exceeding memory limits.

    Raises:
        FileTooLarge: If file content exceeds max_bytes.
    """
    chunks: list[bytes] = []
    total_read = 0
    chunk_size = 64 * 1024  # 64 KB chunks

    while chunk := file.file.read(chunk_size):
        chunks.append(chunk)
        total_read += len(chunk)
        if total_read > max_bytes:
            raise FileTooLarge(f"File exceeds maximum allowed size of {max_bytes} bytes")

    return b"".join(chunks)


def upload_documents(
    uow: UnitOfWork,
    storage: StorageBackend,
    project_id: int,
    user_id: int,
    files: list[UploadFile],
) -> list[Document]:
    """Upload and attach one or more documents to a project.

    Permitted for project owners and participants.
    Validates file extension, magic bytes, project total size limit,
    saves binary contents to the storage backend, and records metadata in the database.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
        ValidationError: if no files provided, empty file, invalid type, or spoofed bytes.
        ProjectQuotaExceeded: if upload would exceed the project size limit.
    """
    require_project_access(
        uow, project_id=project_id, user_id=user_id, action=Action.UPLOAD_DOCUMENT
    )
    project = uow.projects.get_by_id_for_update(project_id)
    if project is None:
        raise ProjectNotFound(f"Project {project_id} not found")

    if not files:
        raise NoFilesProvidedError("No files provided for upload")

    settings = get_settings()
    max_file_size = settings.max_file_size_bytes
    size_limit = settings.project_size_limit_bytes

    # Read and validate all files in memory first
    validated_files: list[tuple[str, str, bytes]] = []
    total_new_bytes = 0

    for file in files:
        if not file.filename:
            raise EmptyFilenameError("Filename cannot be empty")
        content = read_upload_file_limited(file, max_bytes=max_file_size)
        clean_name, mime_type = validate_file_upload(
            filename=file.filename,
            content=content,
            max_size_bytes=max_file_size,
        )
        total_new_bytes += len(content)
        validated_files.append((clean_name, mime_type, content))

    # Check project total size limit
    if project.total_size_bytes + total_new_bytes > size_limit:
        raise ProjectQuotaExceeded(
            f"Project size limit of {size_limit} bytes exceeded "
            f"(current: {project.total_size_bytes}, new upload: {total_new_bytes})"
        )

    # Save files to storage backend and create database records atomically
    saved_storage_keys: list[str] = []
    created_documents: list[Document] = []
    pending_records: list[tuple[Document, str, bytes]] = []

    try:
        with uow:
            for clean_name, mime_type, content in validated_files:
                temp_key = f"pending_{uuid.uuid4().hex}"
                doc = Document(
                    project_id=project.id,
                    filename=clean_name,
                    stored_filename=temp_key,
                    file_size_bytes=len(content),
                    content_type=mime_type,
                )
                uow.documents.add(doc)
                pending_records.append((doc, clean_name, content))

            for doc, clean_name, content in pending_records:
                stored_name = generate_safe_stored_filename(clean_name)
                canonical_key = format_s3_key(project.id, doc.id, stored_name)
                doc.stored_filename = canonical_key
                storage.save(filename=canonical_key, content=content)
                saved_storage_keys.append(canonical_key)
                created_documents.append(doc)

            project.total_size_bytes += total_new_bytes
            uow.commit()

        return created_documents

    except Exception:
        uow.rollback()
        # Clean up any files written to storage on database failure
        for key in saved_storage_keys:
            with contextlib.suppress(Exception):
                storage.delete(key)
        raise


def list_project_documents(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
) -> list[Document]:
    """Retrieve all documents attached to a project.

    Permitted for project owners and participants.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
    """
    require_project_access(
        uow, project_id=project_id, user_id=user_id, action=Action.LIST_DOCUMENTS
    )
    return uow.documents.list_by_project_id(project_id)


def get_document_for_download(
    uow: UnitOfWork,
    storage: StorageBackend,
    document_id: int,
    user_id: int,
) -> tuple[Document, BinaryIO]:
    """Retrieve document metadata and open binary stream for file download.

    Permitted for project owners and participants.

    Raises:
        DocumentNotFound: if document does not exist OR user lacks access.
        StorageFileNotFound: if file is missing from storage.
    """
    doc, _ = require_document_access(
        uow, document_id=document_id, user_id=user_id, action=Action.DOWNLOAD_DOCUMENT
    )
    try:
        stream = storage.get(doc.stored_filename)
    except FileNotFoundError as exc:
        raise StorageFileNotFound(
            f"Stored file for document {document_id} not found in storage"
        ) from exc
    return doc, stream


def replace_document(
    uow: UnitOfWork,
    storage: StorageBackend,
    document_id: int,
    user_id: int,
    file: UploadFile,
) -> Document:
    """Replace a document's file contents with a new upload.

    Permitted for project owners and participants.
    Validates the replacement file, checks project quota with the size delta,
    saves the new file, updates the database, and removes the old file from storage.

    Raises:
        DocumentNotFound: if document does not exist OR user lacks access.
        ValidationError: if file is empty, invalid type, or magic bytes mismatch.
        ProjectQuotaExceeded: if replaced file exceeds the project size limit.
    """
    doc, _ = require_document_access(
        uow, document_id=document_id, user_id=user_id, action=Action.REPLACE_DOCUMENT
    )
    project = uow.projects.get_by_id_for_update(doc.project_id)
    if project is None:
        raise ProjectNotFound(f"Project {doc.project_id} not found")

    if not file.filename:
        raise EmptyFilenameError("Filename cannot be empty")

    settings = get_settings()
    max_file_size = settings.max_file_size_bytes
    size_limit = settings.project_size_limit_bytes

    content = read_upload_file_limited(file, max_bytes=max_file_size)

    clean_name, mime_type = validate_file_upload(
        filename=file.filename,
        content=content,
        max_size_bytes=max_file_size,
    )

    size_delta = len(content) - doc.file_size_bytes
    if project.total_size_bytes + size_delta > size_limit:
        raise ProjectQuotaExceeded(
            f"Project size limit of {size_limit} bytes exceeded "
            f"(current: {project.total_size_bytes}, delta: {size_delta})"
        )

    old_stored_filename = doc.stored_filename
    new_stored_name = generate_safe_stored_filename(clean_name)
    canonical_key = format_s3_key(project.id, doc.id, new_stored_name)

    # Save new file under the canonical key
    storage.save(filename=canonical_key, content=content)

    try:
        with uow:
            doc.filename = clean_name
            doc.stored_filename = canonical_key
            doc.file_size_bytes = len(content)
            doc.content_type = mime_type
            project.total_size_bytes += size_delta
            uow.commit()
    except Exception:
        uow.rollback()
        # If the newly saved key is different from old, clean it up
        if canonical_key != old_stored_filename:
            with contextlib.suppress(Exception):
                storage.delete(canonical_key)
        raise

    # Clean up old file after successful database commit if key changed
    if old_stored_filename != canonical_key:
        with contextlib.suppress(Exception):
            storage.delete(old_stored_filename)

    return doc


def delete_document(
    uow: UnitOfWork,
    storage: StorageBackend,
    document_id: int,
    user_id: int,
) -> None:
    """Delete a document from database and storage backend.

    Permitted for project owners and participants.
    Adjusts the project total_size_bytes accordingly.

    Raises:
        DocumentNotFound: if document does not exist OR user lacks access.
    """
    doc, _ = require_document_access(
        uow, document_id=document_id, user_id=user_id, action=Action.DELETE_DOCUMENT
    )
    project = uow.projects.get_by_id_for_update(doc.project_id)
    stored_key = doc.stored_filename
    doc_size = doc.file_size_bytes

    with uow:
        uow.documents.delete(doc)
        if project is not None:
            project.total_size_bytes = max(0, project.total_size_bytes - doc_size)
        uow.commit()

    with contextlib.suppress(Exception):
        storage.delete(stored_key)
