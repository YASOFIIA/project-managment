from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.projects import (
    create_project,
    delete_project,
    get_project_info,
    list_user_projects,
    update_project_info,
)

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


@router.get(
    "/projects",
    response_model=list[ProjectDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all projects",
    description="Get all projects accessible for the current user, "
    "returning full info with attached documents using raw SQL.",
)
def get_all_projects(
    current_user: CurrentUser,
    db: DbSession,
) -> list[ProjectDetailResponse]:
    """Retrieve all accessible projects with documents."""
    projects = list_user_projects(db=db, user_id=current_user.id)
    return [ProjectDetailResponse.model_validate(p) for p in projects]


@router.get(
    "/project/{project_id}/info",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project info",
    description="Return project's details, if user has access (owner or participant).",
)
def get_info(
    project_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectResponse:
    """Retrieve project details endpoint."""
    project = get_project_info(db=db, project_id=project_id, user_id=current_user.id)
    return ProjectResponse.model_validate(project)


@router.put(
    "/project/{project_id}/info",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project info",
    description="Update project's details - name, description. Returns updated project info.",
)
def update_info(
    project_id: int,
    data: ProjectUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectResponse:
    """Update project details endpoint."""
    project = update_project_info(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        data=data,
    )
    return ProjectResponse.model_validate(project)


@router.delete(
    "/project/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete project and all its associated documents and members. "
    "Permitted for owner only.",
)
def delete_existing_project(
    project_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete project endpoint (owner only)."""
    delete_project(db=db, project_id=project_id, user_id=current_user.id)
