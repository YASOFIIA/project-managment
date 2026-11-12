"""Centralized access control service and permission matrix.

Permission Matrix:
+-------------------+-----------+---------------+--------------------+
| Action            | Owner     | Participant   | Non-Member         |
+-------------------+-----------+---------------+--------------------+
| VIEW              | Allowed   | Allowed       | 404 Not Found      |
| EDIT              | Allowed   | Allowed       | 404 Not Found      |
| DELETE_PROJECT    | Allowed   | 403 Forbidden | 404 Not Found      |
| LIST_DOCUMENTS    | Allowed   | Allowed       | 404 Not Found      |
| UPLOAD_DOCUMENT   | Allowed   | Allowed       | 404 Not Found      |
| DOWNLOAD_DOCUMENT | Allowed   | Allowed       | 404 Not Found      |
| REPLACE_DOCUMENT  | Allowed   | Allowed       | 404 Not Found      |
| DELETE_DOCUMENT   | Allowed   | Allowed       | 404 Not Found      |
| INVITE_MEMBER     | Allowed   | 403 Forbidden | 404 Not Found      |
+-------------------+-----------+---------------+--------------------+

Security Rule:
To prevent user and project enumeration attacks, attempting to access a project
without membership MUST always return 404 Not Found, never revealing whether
the project ID actually exists in the database.
"""

from __future__ import annotations

from app.application.ports.unit_of_work import UnitOfWork
from app.domain.access_policy import Action, can_perform
from app.domain.errors import DocumentNotFound, PermissionDenied, ProjectNotFound
from app.models.document import Document
from app.models.project import Project, ProjectMember


def get_project_membership(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
) -> ProjectMember | None:
    """Retrieve membership record for a user in a specified project, if one exists."""
    return uow.projects.get_membership(project_id=project_id, user_id=user_id)


def require_project_access(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
    action: Action,
) -> tuple[Project, ProjectMember]:
    """Verify that user is a member of the project and has permission to perform action.

    Raises:
        ProjectNotFound: if project does not exist OR user is not a member.
        PermissionDenied: if user is a member but role lacks permission for action.
    """
    membership = uow.projects.get_membership(project_id=project_id, user_id=user_id)
    if membership is None:
        raise ProjectNotFound(f"Project {project_id} not found")

    project = uow.projects.get_by_id(project_id)
    if project is None:
        raise ProjectNotFound(f"Project {project_id} not found")

    if not can_perform(membership.role, action):
        raise PermissionDenied("Only project owner can perform this operation")

    return project, membership


def require_document_access(
    uow: UnitOfWork,
    document_id: int,
    user_id: int,
    action: Action,
) -> tuple[Document, ProjectMember]:
    """Verify that document exists, user is a member, and role has permission for action.

    Raises:
        DocumentNotFound: if document does not exist OR user lacks access to project.
        PermissionDenied: if user is a member but role lacks permission for action.
    """
    document = uow.documents.get_by_id(document_id)
    if document is None:
        raise DocumentNotFound(f"Document {document_id} not found")

    membership = uow.projects.get_membership(project_id=document.project_id, user_id=user_id)
    if membership is None:
        raise DocumentNotFound(f"Document {document_id} not found")

    if not can_perform(membership.role, action):
        raise PermissionDenied("Only project owner can perform this operation")

    return document, membership
