import contextlib
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document
from app.models.project import Project
from app.services.access import require_document_access, require_project_access
from app.services.file_validation import validate_file_upload
from app.storage.base import StorageBackend


def upload_documents(
    db: Session,
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
        HTTPException(404): if project does not exist OR user is not a member.
        HTTPException(400): if no files provided, empty file, invalid type, or spoofed bytes.
        HTTPException(413): if upload would exceed the project size limit.
    """
    project, _ = require_project_access(db, project_id=project_id, user_id=user_id)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload",
        )

    settings = get_settings()
    size_limit = settings.project_size_limit_bytes

    # Read and validate all files in memory first
    validated_files: list[tuple[str, str, str, bytes]] = []
    total_new_bytes = 0

    for file in files:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename cannot be empty",
            )
        content = file.file.read()
        clean_name, safe_stored_name, mime_type = validate_file_upload(
            filename=file.filename,
            content=content,
            max_size_bytes=size_limit,
        )
        total_new_bytes += len(content)
        validated_files.append((clean_name, safe_stored_name, mime_type, content))

    # Check project total size limit
    if project.total_size_bytes + total_new_bytes > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"Project size limit of {size_limit} bytes exceeded "
                f"(current: {project.total_size_bytes}, new upload: {total_new_bytes})"
            ),
        )

    # Save files to storage backend and create database records atomically
    saved_storage_keys: list[str] = []
    created_documents: list[Document] = []

    try:
        for clean_name, safe_stored_name, mime_type, content in validated_files:
            storage.save(filename=safe_stored_name, content=content)
            saved_storage_keys.append(safe_stored_name)

            doc = Document(
                project_id=project.id,
                filename=clean_name,
                stored_filename=safe_stored_name,
                file_size_bytes=len(content),
                content_type=mime_type,
            )
            db.add(doc)
            created_documents.append(doc)

        project.total_size_bytes += total_new_bytes
        db.commit()

        for doc in created_documents:
            db.refresh(doc)

        return created_documents

    except Exception:
        db.rollback()
        # Clean up any files written to storage on database failure
        for key in saved_storage_keys:
            with contextlib.suppress(Exception):
                storage.delete(key)
        raise


def list_project_documents(
    db: Session,
    project_id: int,
    user_id: int,
) -> list[Document]:
    """Retrieve all documents attached to a project.

    Permitted for project owners and participants.

    Raises:
        HTTPException(404): if project does not exist OR user is not a member.
    """
    require_project_access(db, project_id=project_id, user_id=user_id)

    stmt = (
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.asc(), Document.id.asc())
    )
    return list(db.scalars(stmt).all())


def get_document_for_download(
    db: Session,
    storage: StorageBackend,
    document_id: int,
    user_id: int,
) -> tuple[Document, BinaryIO]:
    """Retrieve document metadata and open binary stream for file download.

    Permitted for project owners and participants.

    Raises:
        HTTPException(404): if document does not exist OR user lacks access.
    """
    doc, _ = require_document_access(db, document_id=document_id, user_id=user_id)
    stream = storage.get(doc.stored_filename)
    return doc, stream


def replace_document(
    db: Session,
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
        HTTPException(404): if document does not exist OR user lacks access.
        HTTPException(400): if file is empty, invalid type, or magic bytes mismatch.
        HTTPException(413): if replaced file exceeds the project size limit.
    """
    doc, _ = require_document_access(db, document_id=document_id, user_id=user_id)
    project = db.get(Project, doc.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {doc.project_id} not found",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty",
        )

    content = file.file.read()
    settings = get_settings()
    size_limit = settings.project_size_limit_bytes

    clean_name, safe_stored_name, mime_type = validate_file_upload(
        filename=file.filename,
        content=content,
        max_size_bytes=size_limit,
    )

    size_delta = len(content) - doc.file_size_bytes
    if project.total_size_bytes + size_delta > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"Project size limit of {size_limit} bytes exceeded "
                f"(current: {project.total_size_bytes}, delta: {size_delta})"
            ),
        )

    old_stored_filename = doc.stored_filename

    # Save new file first
    storage.save(filename=safe_stored_name, content=content)

    try:
        doc.filename = clean_name
        doc.stored_filename = safe_stored_name
        doc.file_size_bytes = len(content)
        doc.content_type = mime_type
        project.total_size_bytes += size_delta
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        with contextlib.suppress(Exception):
            storage.delete(safe_stored_name)
        raise

    # Clean up old file after successful database commit
    with contextlib.suppress(Exception):
        storage.delete(old_stored_filename)

    return doc


def delete_document(
    db: Session,
    storage: StorageBackend,
    document_id: int,
    user_id: int,
) -> None:
    """Delete a document from database and storage backend.

    Permitted for project owners and participants.
    Adjusts the project total_size_bytes accordingly.

    Raises:
        HTTPException(404): if document does not exist OR user lacks access.
    """
    doc, _ = require_document_access(db, document_id=document_id, user_id=user_id)
    project = db.get(Project, doc.project_id)
    stored_key = doc.stored_filename
    doc_size = doc.file_size_bytes

    db.delete(doc)
    if project is not None:
        project.total_size_bytes = max(0, project.total_size_bytes - doc_size)

    db.commit()

    with contextlib.suppress(Exception):
        storage.delete(stored_key)
