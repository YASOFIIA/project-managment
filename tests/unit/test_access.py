"""Unit tests for access control and permission enforcement."""

import pytest
from sqlalchemy.orm import Session

from app.application.ports.unit_of_work import UnitOfWork
from app.domain.access_policy import Action
from app.domain.errors import (
    DocumentNotFound,
    NotFoundError,
    PermissionDenied,
    PermissionDeniedError,
    ProjectNotFound,
)
from app.domain.roles import ProjectRole
from app.services.access import (
    require_document_access,
    require_project_access,
)
from tests.factories import (
    create_document,
    create_project,
    create_project_member,
    create_user,
)


def test_require_project_access_for_owner_and_participant(
    uow: UnitOfWork, db_session: Session
) -> None:
    """Verify that both owners and participants pass require_project_access for allowed action."""
    owner = create_user(db_session, login="owner_acc")
    participant = create_user(db_session, login="part_acc")
    project = create_project(db_session, name="Shared Project")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    proj_o, mem_o = require_project_access(uow, project.id, owner.id, action=Action.VIEW)
    assert proj_o.id == project.id
    assert mem_o.role == ProjectRole.OWNER

    proj_p, mem_p = require_project_access(uow, project.id, participant.id, action=Action.VIEW)
    assert proj_p.id == project.id
    assert mem_p.role == ProjectRole.PARTICIPANT


def test_require_project_access_non_member_returns_404(
    uow: UnitOfWork, db_session: Session
) -> None:
    """Verify that a user without membership receives 404 Not Found (information hiding)."""
    user = create_user(db_session, login="stranger")
    project = create_project(db_session, name="Secret Project")

    with pytest.raises(ProjectNotFound) as exc_info:
        require_project_access(uow, project.id, user.id, action=Action.VIEW)

    assert isinstance(exc_info.value, NotFoundError)
    assert f"Project {project.id} not found" in exc_info.value.detail


def test_require_project_access_nonexistent_project_returns_404(
    uow: UnitOfWork, db_session: Session
) -> None:
    """Verify that a non-existent project returns 404 Not Found."""
    user = create_user(db_session, login="user_nonexistent_proj")

    with pytest.raises(ProjectNotFound) as exc_info:
        require_project_access(uow, project_id=999999, user_id=user.id, action=Action.VIEW)

    assert isinstance(exc_info.value, NotFoundError)


def test_require_project_owner_succeeds_for_owner(uow: UnitOfWork, db_session: Session) -> None:
    """Verify that owner passes require_project_access for owner-restricted actions."""
    owner = create_user(db_session, login="real_owner")
    project = create_project(db_session, name="Owner Project")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    proj, mem = require_project_access(uow, project.id, owner.id, action=Action.DELETE_PROJECT)
    assert proj.id == project.id
    assert mem.role == ProjectRole.OWNER


def test_require_project_owner_returns_403_for_participant(
    uow: UnitOfWork, db_session: Session
) -> None:
    """Verify that a participant receives 403 Forbidden for owner-restricted action."""
    participant = create_user(db_session, login="just_participant")
    project = create_project(db_session, name="Protected Project")
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    with pytest.raises(PermissionDenied) as exc_info:
        require_project_access(uow, project.id, participant.id, action=Action.DELETE_PROJECT)

    assert isinstance(exc_info.value, PermissionDeniedError)
    assert "Only project owner" in exc_info.value.detail


def test_require_document_access_succeeds_for_project_members(
    uow: UnitOfWork, db_session: Session
) -> None:
    """Verify that project members can access attached documents."""
    member = create_user(db_session, login="doc_reader")
    project = create_project(db_session, name="Doc Project")
    create_project_member(db_session, project.id, member.id, role=ProjectRole.PARTICIPANT)
    doc = create_document(db_session, project_id=project.id, filename="architecture.pdf")

    found_doc, found_mem = require_document_access(
        uow, doc.id, member.id, action=Action.DOWNLOAD_DOCUMENT
    )
    assert found_doc.id == doc.id
    assert found_mem.role == ProjectRole.PARTICIPANT


def test_require_document_access_non_member_returns_404(
    uow: UnitOfWork, db_session: Session
) -> None:
    """Verify that accessing a document of an unshared project returns 404 Not Found."""
    stranger = create_user(db_session, login="doc_stranger")
    project = create_project(db_session, name="Private Doc Project")
    doc = create_document(db_session, project_id=project.id, filename="confidential.pdf")

    with pytest.raises(DocumentNotFound) as exc_info:
        require_document_access(uow, doc.id, stranger.id, action=Action.DOWNLOAD_DOCUMENT)

    assert isinstance(exc_info.value, NotFoundError)


def test_require_document_access_nonexistent_doc_returns_404(
    uow: UnitOfWork, db_session: Session
) -> None:
    """Verify that non-existent document ID returns 404 Not Found."""
    user = create_user(db_session, login="user_missing_doc")

    with pytest.raises(DocumentNotFound) as exc_info:
        require_document_access(
            uow, document_id=999999, user_id=user.id, action=Action.DOWNLOAD_DOCUMENT
        )

    assert isinstance(exc_info.value, NotFoundError)
