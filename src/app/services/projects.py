from __future__ import annotations

import logging

from app.application.ports.project_repository import ProjectWithDocuments
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
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)


def create_project(
    uow: UnitOfWork,
    user: User,
    data: ProjectCreateRequest,
) -> Project:
    """Create a new project and assign the creator as OWNER in a single atomic transaction."""
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


def list_user_projects(
    uow: UnitOfWork,
    user_id: int,
) -> list[ProjectWithDocuments]:
    """Retrieve all projects accessible to the user with preloaded document metadata."""
    return uow.projects.list_for_user_with_documents(user_id=user_id)


def get_project_info(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
) -> Project:
    """Retrieve project details, verifying the user is an owner or participant.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
    """
    project, _ = require_project_access(
        uow, project_id=project_id, user_id=user_id, action=Action.VIEW
    )
    return project


def update_project_info(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
    data: ProjectUpdateRequest,
) -> Project:
    """Update project details (name, description), permitted for owners and participants.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
    """
    project, _ = require_project_access(
        uow, project_id=project_id, user_id=user_id, action=Action.EDIT
    )

    project.name = data.name.strip()
    project.description = data.description.strip() if data.description else None

    with uow:
        uow.commit()

    return project


def delete_project(
    uow: UnitOfWork,
    storage: StorageBackend,
    project_id: int,
    user_id: int,
) -> None:
    """Delete a project, all its database records, and all attached files from storage.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
        PermissionDenied: if user is a member but not the owner.
    """
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


def invite_member(
    uow: UnitOfWork,
    project_id: int,
    owner_id: int,
    invitee_login: str,
) -> ProjectMember:
    """Invite a user to a project as a participant. Permitted only for the project OWNER.

    Raises:
        ProjectNotFound: if project does not exist OR current user is not a member.
        PermissionDenied: if current user is a participant (not the owner).
        UserNotFound: if user with invitee_login does not exist.
        UserAlreadyMember: if user is already a member of the project.
    """
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
