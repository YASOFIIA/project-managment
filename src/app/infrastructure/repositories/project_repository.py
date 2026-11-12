from __future__ import annotations

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.ports.project_repository import (
    DocumentSummary,
    ProjectWithDocuments,
)
from app.domain.errors import UserAlreadyMember
from app.models.project import Project, ProjectMember

USER_PROJECTS_WITH_DOCUMENTS_SQL = """
SELECT
    p.id AS project_id,
    p.name AS project_name,
    p.description AS project_description,
    p.total_size_bytes AS project_total_size_bytes,
    p.created_at AS project_created_at,
    p.updated_at AS project_updated_at,
    d.id AS document_id,
    d.project_id AS document_project_id,
    d.filename AS document_filename,
    d.file_size_bytes AS document_file_size_bytes,
    d.content_type AS document_content_type,
    d.created_at AS document_created_at
FROM projects p
JOIN project_members pm ON pm.project_id = p.id
LEFT JOIN documents d ON d.project_id = p.id
WHERE pm.user_id = :user_id
ORDER BY p.created_at DESC, d.created_at ASC
"""


class SqlAlchemyProjectRepository:
    """SQLAlchemy adapter for project persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, project_id: int) -> Project | None:
        """Find project by primary key."""
        return self._session.get(Project, project_id)

    def get_by_id_for_update(self, project_id: int) -> Project | None:
        """Find project by primary key with exclusive row lock."""
        stmt = select(Project).where(Project.id == project_id).with_for_update()
        return self._session.scalar(stmt)

    def add(self, project: Project) -> None:
        """Add and flush project entity."""
        self._session.add(project)
        self._session.flush()

    def delete(self, project: Project) -> None:
        """Delete project entity."""
        self._session.delete(project)

    def add_member(self, member: ProjectMember) -> None:
        """Add and flush project membership entity."""
        self._session.add(member)
        try:
            self._session.flush()
        except IntegrityError:
            raise UserAlreadyMember("User is already a member of this project") from None

    def get_membership(self, project_id: int, user_id: int) -> ProjectMember | None:
        """Find project membership for specified user."""
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        return self._session.scalar(stmt)

    def list_for_user_with_documents(self, user_id: int) -> list[ProjectWithDocuments]:
        """Retrieve all projects accessible to user with preloaded document metadata."""
        result = self._session.execute(
            text(USER_PROJECTS_WITH_DOCUMENTS_SQL),
            {"user_id": user_id},
        )
        projects_map: dict[int, tuple[dict[str, Any], list[DocumentSummary]]] = {}

        for row in result.mappings():
            proj_id = row["project_id"]
            if proj_id not in projects_map:
                proj_data = {
                    "id": proj_id,
                    "name": row["project_name"],
                    "description": row["project_description"],
                    "total_size_bytes": row["project_total_size_bytes"],
                    "created_at": row["project_created_at"],
                    "updated_at": row["project_updated_at"],
                }
                projects_map[proj_id] = (proj_data, [])

            if row["document_id"] is not None:
                projects_map[proj_id][1].append(
                    DocumentSummary(
                        id=row["document_id"],
                        project_id=row["document_project_id"],
                        filename=row["document_filename"],
                        file_size_bytes=row["document_file_size_bytes"],
                        content_type=row["document_content_type"],
                        created_at=row["document_created_at"],
                    )
                )

        return [
            ProjectWithDocuments(**data, documents=docs) for data, docs in projects_map.values()
        ]
