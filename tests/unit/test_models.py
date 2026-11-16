import sqlite3
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.domain.roles import ProjectRole
from app.models import Document, Project, ProjectMember, User


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Provide an isolated in-memory SQLite database session with enforced foreign keys
@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


# Check standard creation of User, Project, and ProjectMember
def test_create_user_project_and_membership(db_session: Session) -> None:
    user = User(login="alice", hashed_password="hashed_pw_alice")
    db_session.add(user)
    db_session.commit()

    project = Project(name="Project Alpha", description="Alpha description")
    db_session.add(project)
    db_session.commit()

    member = ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.OWNER)
    db_session.add(member)
    db_session.commit()

    # Verify relationships
    db_session.refresh(project)
    db_session.refresh(user)
    assert len(project.members) == 1
    assert project.members[0].user_id == user.id
    assert project.members[0].role == ProjectRole.OWNER
    assert len(user.memberships) == 1
    assert user.memberships[0].project_id == project.id


# Check a user cannot be added twice to the same project
def test_unique_project_member_constraint(db_session: Session) -> None:
    user = User(login="bob", hashed_password="hashed_pw_bob")
    project = Project(name="Project Beta")
    db_session.add_all([user, project])
    db_session.commit()

    member1 = ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.OWNER)
    db_session.add(member1)
    db_session.commit()

    member2 = ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.PARTICIPANT)
    db_session.add(member2)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# Check deleting a project cascades to its documents and project_members
def test_cascade_delete_project_removes_documents_and_members(db_session: Session) -> None:
    user = User(login="charlie", hashed_password="hashed_pw_charlie")
    project = Project(name="Project Gamma")
    db_session.add_all([user, project])
    db_session.commit()

    member = ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.OWNER)
    document = Document(
        project_id=project.id,
        filename="specs.pdf",
        stored_filename="uuid-specs.pdf",
        file_size_bytes=1024,
        content_type="application/pdf",
    )
    db_session.add_all([member, document])
    db_session.commit()

    project_id = project.id
    doc_id = document.id
    member_id = member.id

    # Delete project
    db_session.delete(project)
    db_session.commit()
    db_session.expire_all()

    # Documents and members must be cascaded
    assert db_session.get(Project, project_id) is None
    assert db_session.get(Document, doc_id) is None
    assert db_session.get(ProjectMember, member_id) is None
    # User must still exist
    assert db_session.get(User, user.id) is not None


# Check stored_filename enforces unique constraint across documents
def test_document_stored_filename_must_be_unique(db_session: Session) -> None:
    project = Project(name="Project Delta")
    db_session.add(project)
    db_session.commit()

    doc1 = Document(
        project_id=project.id,
        filename="file1.pdf",
        stored_filename="same_unique_key.pdf",
        file_size_bytes=500,
        content_type="application/pdf",
    )
    doc2 = Document(
        project_id=project.id,
        filename="file2.pdf",
        stored_filename="same_unique_key.pdf",
        file_size_bytes=700,
        content_type="application/pdf",
    )
    db_session.add(doc1)
    db_session.commit()

    db_session.add(doc2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# Check duplicate user logins are rejected by unique constraint
def test_user_login_must_be_unique(db_session: Session) -> None:
    u1 = User(login="dave", hashed_password="pw1")
    u2 = User(login="dave", hashed_password="pw2")

    db_session.add(u1)
    db_session.commit()

    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
