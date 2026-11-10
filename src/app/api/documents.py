from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.document import DocumentResponse
from app.services.documents import (
    delete_document,
    get_document_for_download,
    list_project_documents,
    replace_document,
    upload_documents,
)
from app.storage import get_storage
from app.storage.base import StorageBackend

router = APIRouter(tags=["Documents"])

DbSession = Annotated[Session, Depends(get_db)]
StorageDep = Annotated[StorageBackend, Depends(get_storage)]


@router.post(
    "/project/{project_id}/documents",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload documents to project",
    description="Upload one or multiple files (PDF, DOCX, PNG, JPG/JPEG) to a project. "
    "Permitted for project owners and participants.",
)
def upload_files(
    project_id: int,
    files: list[UploadFile],
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
) -> list[DocumentResponse]:
    """Upload documents endpoint."""
    documents = upload_documents(
        db=db,
        storage=storage,
        project_id=project_id,
        user_id=current_user.id,
        files=files,
    )
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/project/{project_id}/documents",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List project documents",
    description="Retrieve all documents attached to a project. "
    "Permitted for project owners and participants.",
)
def get_documents(
    project_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> list[DocumentResponse]:
    """List documents endpoint."""
    documents = list_project_documents(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
    )
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/document/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Download document",
    description="Download a document's binary file content. "
    "Permitted for project owners and participants.",
)
def download_file(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
) -> StreamingResponse:
    """Download document endpoint."""
    doc, stream = get_document_for_download(
        db=db,
        storage=storage,
        document_id=document_id,
        user_id=current_user.id,
    )
    # RFC 5987 encoded filename for non-ASCII safety
    encoded_filename = quote(doc.filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        "Content-Length": str(doc.file_size_bytes),
    }
    return StreamingResponse(stream, media_type=doc.content_type, headers=headers)


@router.put(
    "/document/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Replace document file",
    description="Replace an existing document's file content and update its metadata. "
    "Permitted for project owners and participants.",
)
def update_file(
    document_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
) -> DocumentResponse:
    """Replace document endpoint."""
    doc = replace_document(
        db=db,
        storage=storage,
        document_id=document_id,
        user_id=current_user.id,
        file=file,
    )
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/document/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description="Delete a document from the database and storage backend. "
    "Permitted for project owners and participants.",
)
def delete_file(
    document_id: int,
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
) -> None:
    """Delete document endpoint."""
    delete_document(
        db=db,
        storage=storage,
        document_id=document_id,
        user_id=current_user.id,
    )
