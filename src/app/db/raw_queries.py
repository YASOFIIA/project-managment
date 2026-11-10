from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

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


def get_user_projects_with_documents_raw(
    db: Session,
    user_id: int,
) -> list[dict[str, Any]]:
    """Retrieve all projects accessible to a user with attached documents using raw SQL.

    Employs a single SQL JOIN to eliminate the N+1 query problem without ORM overhead.
    Never uses string concatenation to prevent SQL injection.
    """
    result = db.execute(
        text(USER_PROJECTS_WITH_DOCUMENTS_SQL),
        {"user_id": user_id},
    )

    projects_map: dict[int, dict[str, Any]] = {}

    for row in result.mappings():
        proj_id = row["project_id"]
        if proj_id not in projects_map:
            projects_map[proj_id] = {
                "id": proj_id,
                "name": row["project_name"],
                "description": row["project_description"],
                "total_size_bytes": row["project_total_size_bytes"],
                "created_at": row["project_created_at"],
                "updated_at": row["project_updated_at"],
                "documents": [],
            }

        # If a document exists for this row (LEFT JOIN might return NULLs)
        if row["document_id"] is not None:
            projects_map[proj_id]["documents"].append(
                {
                    "id": row["document_id"],
                    "project_id": row["document_project_id"],
                    "filename": row["document_filename"],
                    "file_size_bytes": row["document_file_size_bytes"],
                    "content_type": row["document_content_type"],
                    "created_at": row["document_created_at"],
                }
            )

    return list(projects_map.values())


def get_user_projects_with_documents_orm(
    db: Session,
    user_id: int,
) -> list[Project]:
    """Retrieve user projects using SQLAlchemy ORM with selectinload for comparison."""
    stmt = (
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user_id)
        .options(selectinload(Project.documents))
        .order_by(Project.created_at.desc())
    )
    return list(db.scalars(stmt).all())
