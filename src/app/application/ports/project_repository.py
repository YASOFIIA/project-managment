from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.models.project import Project, ProjectMember


@dataclass(frozen=True)
class DocumentSummary:
    """Read model for attached document metadata."""

    id: int
    project_id: int
    filename: str
    file_size_bytes: int
    content_type: str
    created_at: datetime


@dataclass(frozen=True)
class ProjectWithDocuments:
    """Read model for project with preloaded document metadata."""

    id: int
    name: str
    description: str | None
    total_size_bytes: int
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentSummary] = field(default_factory=list)


class ProjectRepository(Protocol):
    """Port for project and project membership persistence operations."""

    def get_by_id(self, project_id: int) -> Project | None:
        """Find project by primary key."""
        ...

    def get_by_id_for_update(self, project_id: int) -> Project | None:
        """Find project by primary key with exclusive row lock (FOR UPDATE)."""
        ...

    def add(self, project: Project) -> None:
        """Add and flush project entity."""
        ...

    def delete(self, project: Project) -> None:
        """Delete project entity."""
        ...

    def add_member(self, member: ProjectMember) -> None:
        """Add and flush project membership entity."""
        ...

    def get_membership(self, project_id: int, user_id: int) -> ProjectMember | None:
        """Find project membership for specified user."""
        ...

    def list_for_user_with_documents(self, user_id: int) -> list[ProjectWithDocuments]:
        """Retrieve all projects accessible to user with preloaded document metadata."""
        ...
