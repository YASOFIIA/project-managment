# Access control service and permission checks
from __future__ import annotations

from app.application.ports.unit_of_work import UnitOfWork
from app.domain.access_policy import Action, can_perform
from app.domain.errors import DocumentNotFound, PermissionDenied, ProjectNotFound
from app.models.document import Document
from app.models.project import Project, ProjectMember


# Get user membership in project if exists
def get_project_membership(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
) -> ProjectMember | None:
    return uow.projects.get_membership(project_id=project_id, user_id=user_id)


# Check user has permission for action on project
def require_project_access(
    uow: UnitOfWork,
    project_id: int,
    user_id: int,
    action: Action,
) -> tuple[Project, ProjectMember]:
    membership = uow.projects.get_membership(project_id=project_id, user_id=user_id)
    if membership is None:
        raise ProjectNotFound(f"Project {project_id} not found")

    project = uow.projects.get_by_id(project_id)
    if project is None:
        raise ProjectNotFound(f"Project {project_id} not found")

    if not can_perform(membership.role, action):
        raise PermissionDenied("Only project owner can perform this operation")

    return project, membership


# Check user has permission for action on document
def require_document_access(
    uow: UnitOfWork,
    document_id: int,
    user_id: int,
    action: Action,
) -> tuple[Document, ProjectMember]:
    document = uow.documents.get_by_id(document_id)
    if document is None:
        raise DocumentNotFound(f"Document {document_id} not found")

    membership = uow.projects.get_membership(project_id=document.project_id, user_id=user_id)
    if membership is None:
        raise DocumentNotFound(f"Document {document_id} not found")

    if not can_perform(membership.role, action):
        raise PermissionDenied("Only project owner can perform this operation")

    return document, membership
