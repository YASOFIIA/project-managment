from __future__ import annotations

import logging

from app.application.ports.project_repository import ProjectWithDocuments
from app.application.ports.storage import StorageBackend
from app.application.ports.unit_of_work import UnitOfWork
from app.domain.access_policy import Action
from app.domain.errors import UserAlreadyMember, UserNotFound
from app.domain.roles import ProjectRole
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.services.access import (
    get_project_membership,
    require_project_access,
)

logger = logging.getLogger(__name__)


# Create project and assign creator as owner
def create_project(
    uow: UnitOfWork,
    user: User,
    data: ProjectCreateRequest,
) -> Project:
    with uow:
        project = Project(
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            total_size_bytes=0,
        )
        uow.projects.add(project)

        membership = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role=ProjectRole.OWNER,
        )
        uow.projects.add_member(membership)
        uow.commit()
        return project


# List all accessible projects with documents
def list_user_projects(
    uow: UnitOfWork,
    user_id: int,
) -> list[ProjectWithDocuments]:
    return uow.projects.list_for_user_with_documents(user_id=user_id)


# Get project details for owner or participant
def get_project_info(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
) -> Project:
    project, _ = require_project_access(
        uow, project_id=project_id, user_id=user_id, action=Action.VIEW
    )
    return project


# List project members, visible to owner and participants
def list_project_members(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
) -> list[ProjectMember]:
    require_project_access(uow, project_id=project_id, user_id=user_id, action=Action.VIEW)
    return uow.projects.list_members(project_id)


# Update project details (name, description)
def update_project_info(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
    data: ProjectUpdateRequest,
) -> Project:
    project, _ = require_project_access(
        uow, project_id=project_id, user_id=user_id, action=Action.EDIT
    )

    project.name = data.name.strip()
    project.description = data.description.strip() if data.description else None

    with uow:
        uow.commit()

    return project


# Delete project, records, and files from storage
def delete_project(
    uow: UnitOfWork,
    storage: StorageBackend,
    project_id: int,
    user_id: int,
) -> None:
    project, _ = require_project_access(
        uow, project_id=project_id, user_id=user_id, action=Action.DELETE_PROJECT
    )

    stored_filenames = uow.documents.list_stored_filenames(project_id)

    with uow:
        uow.projects.delete(project)
        uow.commit()

    for stored_file in stored_filenames:
        try:
            storage.delete(stored_file)
        except Exception as exc:
            logger.warning(
                "Failed to remove file '%s' from storage after project %d deletion: %s",
                stored_file,
                project_id,
                exc,
            )


# Invite user to project as participant (owner only)
def invite_member(
    uow: UnitOfWork,
    project_id: int,
    owner_id: int,
    invitee_login: str,
) -> ProjectMember:
    require_project_access(
        uow, project_id=project_id, user_id=owner_id, action=Action.INVITE_MEMBER
    )

    invitee = uow.users.get_by_login(invitee_login)
    if invitee is None:
        raise UserNotFound(f"User '{invitee_login}' not found")

    existing = get_project_membership(uow, project_id=project_id, user_id=invitee.id)
    if existing is not None:
        raise UserAlreadyMember(f"User '{invitee_login}' is already a member of this project")

    membership = ProjectMember(
        project_id=project_id,
        user_id=invitee.id,
        role=ProjectRole.PARTICIPANT,
    )
    with uow:
        try:
            uow.projects.add_member(membership)
            uow.commit()
        except UserAlreadyMember:
            uow.rollback()
            raise

    return membership
