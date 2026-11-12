import contextlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.raw_queries import get_user_projects_with_documents_raw
from app.domain.errors import UserAlreadyMember, UserNotFound
from app.models.document import Document
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.services.access import (
    get_project_membership,
    require_project_access,
    require_project_owner,
)
from app.storage.base import StorageBackend


def create_project(
    db: Session,
    user: User,
    data: ProjectCreateRequest,
) -> Project:
    """Create a new project and assign the creator as OWNER in a single atomic transaction."""
    project = Project(
        name=data.name.strip(),
        description=data.description.strip() if data.description else None,
        total_size_bytes=0,
    )
    db.add(project)
    db.flush()

    # Automatically grant creator owner permissions
    membership = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=ProjectRole.OWNER,
    )
    db.add(membership)

    db.commit()
    db.refresh(project)
    return project


def list_user_projects(
    db: Session,
    user_id: int,
) -> list[dict[str, Any]]:
    """Retrieve all projects accessible to the user with attached documents using raw SQL."""
    return get_user_projects_with_documents_raw(db=db, user_id=user_id)


def get_project_info(
    db: Session,
    project_id: int,
    user_id: int,
) -> Project:
    """Retrieve project details, verifying the user is an owner or participant.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
    """
    project, _ = require_project_access(db, project_id=project_id, user_id=user_id)
    return project


def update_project_info(
    db: Session,
    project_id: int,
    user_id: int,
    data: ProjectUpdateRequest,
) -> Project:
    """Update project details (name, description), permitted for owners and participants.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
    """
    project, _ = require_project_access(db, project_id=project_id, user_id=user_id)

    project.name = data.name.strip()
    project.description = data.description.strip() if data.description else None

    db.commit()
    db.refresh(project)
    return project


def delete_project(
    db: Session,
    storage: StorageBackend,
    project_id: int,
    user_id: int,
) -> None:
    """Delete a project, all its database records, and all attached files from storage.

    Associated database records (documents, memberships) are removed via foreign key cascades.
    Physical files attached to project documents are removed from the storage backend.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
        PermissionDenied: if user is a member but not the owner.
    """
    project, _ = require_project_owner(db, project_id=project_id, user_id=user_id)

    # Collect stored document filenames before cascading deletion removes DB rows
    stored_filenames = list(
        db.scalars(select(Document.stored_filename).where(Document.project_id == project_id)).all()
    )

    db.delete(project)
    db.commit()

    # Clean up physical files from storage backend
    for stored_file in stored_filenames:
        with contextlib.suppress(Exception):
            storage.delete(stored_file)


def invite_member(
    db: Session,
    project_id: int,
    owner_id: int,
    invitee_login: str,
) -> ProjectMember:
    """Invite a user to a project as a participant.

    Permitted only for the project OWNER.

    Raises:
        ProjectNotFound: if project does not exist OR current user is not a member.
        PermissionDenied: if current user is a participant (not the owner).
        UserNotFound: if user with invitee_login does not exist.
        UserAlreadyMember: if user is already a member of the project (owner or participant).
    """
    # 1. Access check: owner only (raises 404 if project/membership missing, 403 if participant)
    require_project_owner(db, project_id=project_id, user_id=owner_id)

    # 2. Check that target invitee exists
    invitee = db.scalar(select(User).where(User.login == invitee_login))
    if invitee is None:
        raise UserNotFound(f"User '{invitee_login}' not found")

    # 3. Check if invitee is already a member
    existing = get_project_membership(db, project_id=project_id, user_id=invitee.id)
    if existing is not None:
        raise UserAlreadyMember(f"User '{invitee_login}' is already a member of this project")

    # 4. Create membership as PARTICIPANT
    membership = ProjectMember(
        project_id=project_id,
        user_id=invitee.id,
        role=ProjectRole.PARTICIPANT,
    )
    db.add(membership)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise UserAlreadyMember(
            f"User '{invitee_login}' is already a member of this project"
        ) from None
    db.refresh(membership)
    return membership
