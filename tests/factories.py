import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import Document, Project, ProjectMember, ProjectRole, User


def create_user(
    session: Session,
    login: str | None = None,
    hashed_password: str = "hashed_dummy_password",
    **kwargs: Any,
) -> User:
    """Factory helper to create and persist a User entity."""
    user = User(
        login=login or f"user_{uuid.uuid4().hex[:8]}",
        hashed_password=hashed_password,
        **kwargs,
    )
    session.add(user)
    session.flush()
    return user


def create_project(
    session: Session,
    name: str | None = None,
    description: str | None = "Default test project description",
    total_size_bytes: int = 0,
    **kwargs: Any,
) -> Project:
    """Factory helper to create and persist a Project entity."""
    project = Project(
        name=name or f"Project {uuid.uuid4().hex[:6]}",
        description=description,
        total_size_bytes=total_size_bytes,
        **kwargs,
    )
    session.add(project)
    session.flush()
    return project


def create_project_member(
    session: Session,
    project_id: int,
    user_id: int,
    role: ProjectRole = ProjectRole.OWNER,
    **kwargs: Any,
) -> ProjectMember:
    """Factory helper to create and persist a ProjectMember entity."""
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        **kwargs,
    )
    session.add(member)
    session.flush()
    return member


def create_document(
    session: Session,
    project_id: int,
    filename: str = "report.pdf",
    stored_filename: str | None = None,
    file_size_bytes: int = 1024,
    content_type: str = "application/pdf",
    **kwargs: Any,
) -> Document:
    """Factory helper to create and persist a Document entity."""
    temp_stored = stored_filename or f"pending_{uuid.uuid4().hex}"
    document = Document(
        project_id=project_id,
        filename=filename,
        stored_filename=temp_stored,
        file_size_bytes=file_size_bytes,
        content_type=content_type,
        **kwargs,
    )
    session.add(document)
    session.flush()
    if stored_filename is None:
        document.stored_filename = f"projects/{project_id}/{document.id}/{uuid.uuid4().hex}.pdf"
        session.flush()
    return document
