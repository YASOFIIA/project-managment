from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, EmailSenderDep, UowDep
from app.application.ports.storage import StorageBackend
from app.core.config import Settings, get_settings
from app.schemas.project import (
    InvitationResponse,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.invitations import create_and_send_invitation
from app.services.projects import (
    create_project,
    delete_project,
    get_project_info,
    invite_member,
    list_user_projects,
    update_project_info,
)
from app.storage import get_storage

router = APIRouter(tags=["Projects"])

StorageDep = Annotated[StorageBackend, Depends(get_storage)]


# Create project endpoint
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
    uow: UowDep,
) -> ProjectResponse:
    project = create_project(uow=uow, user=current_user, data=data)
    return ProjectResponse.model_validate(project)


# Get all accessible projects endpoint
@router.get(
    "/projects",
    response_model=list[ProjectDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all projects",
    description="Get all projects accessible for the current user, "
    "returning full info with attached documents.",
)
def get_all_projects(
    current_user: CurrentUser,
    uow: UowDep,
) -> list[ProjectDetailResponse]:
    projects = list_user_projects(uow=uow, user_id=current_user.id)
    return [ProjectDetailResponse.model_validate(p) for p in projects]


# Get project details endpoint
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
    uow: UowDep,
) -> ProjectResponse:
    project = get_project_info(uow=uow, project_id=project_id, user_id=current_user.id)
    return ProjectResponse.model_validate(project)


# Update project details endpoint
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
    uow: UowDep,
) -> ProjectResponse:
    project = update_project_info(
        uow=uow,
        project_id=project_id,
        user_id=current_user.id,
        data=data,
    )
    return ProjectResponse.model_validate(project)


# Delete project endpoint (owner only)
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
    uow: UowDep,
    storage: StorageDep,
) -> None:
    delete_project(
        uow=uow,
        storage=storage,
        project_id=project_id,
        user_id=current_user.id,
    )


# Invite user endpoint (owner only)
@router.post(
    "/project/{project_id}/invite",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Invite user to project",
    description="Invite a user to the project as a participant. Permitted for owner only.",
)
def invite_user_to_project(
    project_id: int,
    current_user: CurrentUser,
    uow: UowDep,
    user: str = Query(..., min_length=1, description="Username of user to invite"),
) -> ProjectMemberResponse:
    membership = invite_member(
        uow=uow,
        project_id=project_id,
        owner_id=current_user.id,
        invitee_login=user,
    )
    return ProjectMemberResponse.model_validate(membership)


# Share project via email endpoint (owner only)
@router.get(
    "/project/{project_id}/share",
    response_model=InvitationResponse,
    status_code=status.HTTP_200_OK,
    summary="Share project via email invitation",
    description=(
        "Generate a secure invitation token and send a share link via email. "
        "Permitted for owner only."
    ),
)
def share_project_via_email(
    project_id: int,
    current_user: CurrentUser,
    uow: UowDep,
    email_sender: EmailSenderDep,
    email: Annotated[str, Query(alias="with", min_length=3, description="Recipient email address")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InvitationResponse:
    return create_and_send_invitation(
        uow=uow,
        email_sender=email_sender,
        project_id=project_id,
        owner_id=current_user.id,
        email=email,
        base_url=settings.app_base_url,
        expire_hours=settings.invitation_expire_hours,
    )
