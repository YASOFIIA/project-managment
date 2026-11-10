from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.project import ProjectCreateRequest, ProjectResponse
from app.services.projects import create_project

router = APIRouter(tags=["Projects"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
    description="Create project from details (name, description). "
    "Automatically makes the creator the project owner.",
)
def create_new_project(
    data: ProjectCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectResponse:
    """Create a new project endpoint."""
    project = create_project(db=db, user=current_user, data=data)
    return ProjectResponse.model_validate(project)
