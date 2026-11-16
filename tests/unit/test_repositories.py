from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.ports.project_repository import ProjectWithDocuments
from app.application.ports.unit_of_work import UnitOfWork
from app.domain.roles import ProjectRole
from app.infrastructure.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.repositories.project_repository import (
    SqlAlchemyProjectRepository,
)
from app.infrastructure.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from app.models.document import Document
from app.models.project import Project, ProjectMember
from app.models.user import User


def test_user_repository_crud(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = User(
        login="repo_user",
        email="repo_user@example.com",
        hashed_password="hashed_password_123",
    )
    repo.add(user)
    assert user.id is not None

    found_by_id = repo.get_by_id(user.id)
    assert found_by_id is not None
    assert found_by_id.login == "repo_user"

    found_by_login = repo.get_by_login("repo_user")
    assert found_by_login is not None
    assert found_by_login.id == user.id

    found_by_email = repo.get_by_email("repo_user@example.com")
    assert found_by_email is not None
    assert found_by_email.id == user.id

    assert repo.get_by_login("nonexistent") is None
    assert repo.get_by_email("missing@example.com") is None


def test_project_repository_crud_and_membership(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    proj_repo = SqlAlchemyProjectRepository(db_session)

    user = User(login="proj_owner", email="proj_owner@example.com", hashed_password="pwd")
    user_repo.add(user)

    project = Project(name="Repo Project", description="Test Description")
    proj_repo.add(project)
    assert project.id is not None

    member = ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.OWNER)
    proj_repo.add_member(member)

    found_project = proj_repo.get_by_id(project.id)
    assert found_project is not None
    assert found_project.name == "Repo Project"

    locked_proj = proj_repo.get_by_id_for_update(project.id)
    assert locked_proj is not None
    assert locked_proj.id == project.id

    membership = proj_repo.get_membership(project.id, user.id)
    assert membership is not None
    assert membership.role == ProjectRole.OWNER

    found_member = proj_repo.get_member_by_id(member.id)
    assert found_member is not None
    assert found_member.id == member.id

    projects = proj_repo.list_for_user_with_documents(user.id)
    assert len(projects) == 1
    assert isinstance(projects[0], ProjectWithDocuments)
    assert projects[0].id == project.id
    assert projects[0].documents == []

    proj_repo.delete(project)
    db_session.flush()
    assert proj_repo.get_by_id(project.id) is None


def test_document_repository_crud_and_filenames(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    proj_repo = SqlAlchemyProjectRepository(db_session)
    doc_repo = SqlAlchemyDocumentRepository(db_session)

    user = User(login="doc_owner", email="doc_owner@example.com", hashed_password="pwd")
    user_repo.add(user)

    project = Project(name="Doc Project")
    proj_repo.add(project)

    doc1 = Document(
        project_id=project.id,
        filename="report1.pdf",
        stored_filename="projects/1/1/uuid1.pdf",
        file_size_bytes=100,
        content_type="application/pdf",
    )
    doc2 = Document(
        project_id=project.id,
        filename="report2.pdf",
        stored_filename="projects/1/2/uuid2.pdf",
        file_size_bytes=200,
        content_type="application/pdf",
    )
    doc_repo.add(doc1)
    doc_repo.add(doc2)

    docs = doc_repo.list_by_project_id(project.id)
    assert len(docs) == 2

    keys = doc_repo.list_stored_filenames(project.id)
    assert keys == ["projects/1/1/uuid1.pdf", "projects/1/2/uuid2.pdf"]

    found = doc_repo.get_by_id(doc1.id)
    assert found is not None
    assert found.filename == "report1.pdf"

    projects_with_docs = proj_repo.list_for_user_with_documents(user.id)
    # user is not a member yet, so empty
    assert len(projects_with_docs) == 0

    member = ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.OWNER)
    proj_repo.add_member(member)

    projects_with_docs = proj_repo.list_for_user_with_documents(user.id)
    assert len(projects_with_docs) == 1
    assert len(projects_with_docs[0].documents) == 2
    assert projects_with_docs[0].documents[0].filename == "report1.pdf"

    doc_repo.delete(doc1)
    db_session.flush()
    assert doc_repo.get_by_id(doc1.id) is None


def test_unit_of_work_lifecycle_and_rollback(uow: UnitOfWork, db_session: Session) -> None:
    with uow:
        user = User(login="uow_user", email="uow_user@example.com", hashed_password="pwd")
        uow.users.add(user)
        uow.commit()

    assert uow.users.get_by_login("uow_user") is not None

    with pytest.raises(RuntimeError), uow:
        user2 = User(login="uow_fail", email="uow_fail@example.com", hashed_password="pwd")
        uow.users.add(user2)
        raise RuntimeError("Force failure")

    assert uow.users.get_by_login("uow_fail") is None


def test_unit_of_work_exit_calls_rollback_on_exception(db_session: Session) -> None:
    uow = SqlAlchemyUnitOfWork(db_session)
    with (
        patch.object(uow, "rollback", wraps=uow.rollback) as spy_rollback,
        pytest.raises(ValueError),
        uow,
    ):
        raise ValueError("Boom")
    spy_rollback.assert_called_once()


def test_project_repository_add_member_fk_violation_raises_integrity_error(
    db_session: Session,
) -> None:
    proj_repo = SqlAlchemyProjectRepository(db_session)
    non_existent_member = ProjectMember(
        project_id=999999,
        user_id=999999,
        role=ProjectRole.PARTICIPANT,
    )
    with pytest.raises(IntegrityError):
        proj_repo.add_member(non_existent_member)


def test_user_repository_non_unique_integrity_error_is_reraised(db_session: Session) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = User(login="fk_test_user", email="fk_test_user@example.com", hashed_password="pwd")
    mock_orig = Exception("FK violation")
    mock_orig.sqlstate = "23503"  # type: ignore[attr-defined]
    mock_orig.pgcode = "23503"  # type: ignore[attr-defined]
    fake_err = IntegrityError("INSERT failed FK", params=None, orig=mock_orig)

    with patch.object(db_session, "flush", side_effect=fake_err), pytest.raises(IntegrityError):
        repo.add(user)
