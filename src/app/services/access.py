"""Centralized access control service and permission matrix.

Permission Matrix:
+------------------------------------+-----------+---------------+-------------------------+
| Action / Endpoint                  | Owner     | Participant   | No Access / Non-Member  |
+------------------------------------+-----------+---------------+-------------------------+
| View info (GET /project/<id>/info) | Allowed   | Allowed       | 404 (hide existence)    |
| Edit info (PUT /project/<id>/info) | Allowed   | Allowed       | 404 (hide existence)    |
| Delete project (DELETE /project/<id>)| Allowed | 403 Forbidden | 404 (hide existence)    |
| List documents (GET /project/<id>/docs)| Allowed | Allowed     | 404 (hide existence)    |
| Upload doc (POST /project/<id>/docs)  | Allowed | Allowed       | 404 (hide existence)    |
| Download doc (GET /document/<id>)  | Allowed   | Allowed       | 404 (hide existence)    |
| Replace doc (PUT /document/<id>)   | Allowed   | Allowed       | 404 (hide existence)    |
| Delete doc (DELETE /document/<id>) | Allowed   | Allowed       | 404 (hide existence)    |
| Invite user (POST /project/<id>/invite)| Allowed| 403 Forbidden | 404 (hide existence)    |
+------------------------------------+-----------+---------------+-------------------------+

Security Rule:
To prevent user and project enumeration attacks, attempting to access a project
without membership MUST always return 404 Not Found, never revealing whether
the project ID actually exists in the database.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import DocumentNotFound, PermissionDenied, ProjectNotFound
from app.models.document import Document
from app.models.project import Project, ProjectMember, ProjectRole


def get_project_membership(
    db: Session,
    project_id: int,
    user_id: int,
) -> ProjectMember | None:
    """Retrieve membership record for a user in a specified project, if one exists."""
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    return db.scalar(stmt)


def require_project_access(
    db: Session,
    project_id: int,
    user_id: int,
) -> tuple[Project, ProjectMember]:
    """Verify that user is a member of the project.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
    """
    membership = get_project_membership(db, project_id=project_id, user_id=user_id)
    if membership is None:
        raise ProjectNotFound(f"Project {project_id} not found")

    project = db.get(Project, project_id)
    if project is None:
        raise ProjectNotFound(f"Project {project_id} not found")

    return project, membership


def require_project_owner(
    db: Session,
    project_id: int,
    user_id: int,
) -> tuple[Project, ProjectMember]:
    """Verify that user is specifically the OWNER of the project.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
        PermissionDenied: if user is a member but does not have the owner role.
    """
    project, membership = require_project_access(db, project_id=project_id, user_id=user_id)

    if membership.role != ProjectRole.OWNER:
        raise PermissionDenied("Only project owner can perform this operation")

    return project, membership


def require_document_access(
    db: Session,
    document_id: int,
    user_id: int,
) -> tuple[Document, ProjectMember]:
    """Verify that document exists and the user has access to its enclosing project.

    Raises:
        DocumentNotFound: if document does not exist OR user lacks access to project.
    """
    document = db.get(Document, document_id)
    if document is None:
        raise DocumentNotFound(f"Document {document_id} not found")

    membership = get_project_membership(db, project_id=document.project_id, user_id=user_id)
    if membership is None:
        raise DocumentNotFound(f"Document {document_id} not found")

    return document, membership
