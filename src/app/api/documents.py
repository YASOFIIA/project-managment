from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.document import DocumentResponse
from app.services.documents import list_project_documents, upload_documents
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
