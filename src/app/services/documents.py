import contextlib

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document
from app.services.access import require_project_access
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
