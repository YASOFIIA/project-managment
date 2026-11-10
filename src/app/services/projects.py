import contextlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.raw_queries import get_user_projects_with_documents_raw
from app.models.document import Document
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User
from app.schemas.project import ProjectCreateRequest, ProjectUpdateRequest
from app.services.access import require_project_access, require_project_owner
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
        HTTPException(404): if project does not exist OR user is not a member.
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
        HTTPException(404): if project does not exist OR user is not a member.
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
        HTTPException(404): if project does not exist OR user is not a member.
        HTTPException(403): if user is a member but not the owner.
    """
    project, _ = require_project_owner(db, project_id=project_id, user_id=user_id)

    # Collect stored document filenames before cascading deletion removes DB rows
    stored_filenames = list(
        db.scalars(select(Document.stored_filename).where(Document.project_id == project_id)).all()
    )

    # Collect stored document filenames before cascading deletion removes DB rows
    stored_filenames = list(
        db.scalars(
            select(Document.stored_filename).where(Document.project_id == project_id)
        ).all()
    )

    db.delete(project)
    db.commit()

    # Clean up physical files from storage backend
    for stored_file in stored_filenames:
        with contextlib.suppress(Exception):
            storage.delete(stored_file)

    # Clean up physical files from storage backend
    for stored_file in stored_filenames:
        with contextlib.suppress(Exception):
            storage.delete(stored_file)

