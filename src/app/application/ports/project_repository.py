from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.models.project import Project, ProjectMember


# Read model for document metadata
@dataclass(frozen=True)
class DocumentSummary:
    id: int
    project_id: int
    filename: str
    file_size_bytes: int
    content_type: str
    created_at: datetime


# Read model for project with documents
@dataclass(frozen=True)
class ProjectWithDocuments:
    id: int
    name: str
    description: str | None
    total_size_bytes: int
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentSummary] = field(default_factory=list)


# Project repository port
class ProjectRepository(Protocol):
    # Find project by primary key
    def get_by_id(self, project_id: int) -> Project | None: ...

    # Find project with row lock (FOR UPDATE)
    def get_by_id_for_update(self, project_id: int) -> Project | None: ...

    # Add and flush project
    def add(self, project: Project) -> None: ...

    # Delete project
    def delete(self, project: Project) -> None: ...

    # Add and flush project membership
    def add_member(self, member: ProjectMember) -> None: ...

    # Find user membership in project
    def get_membership(self, project_id: int, user_id: int) -> ProjectMember | None: ...

    # List all members of a project (with users loaded)
    def list_members(self, project_id: int) -> list[ProjectMember]: ...

    # List user projects with documents
    def list_for_user_with_documents(self, user_id: int) -> list[ProjectWithDocuments]: ...
