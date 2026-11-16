from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.roles import ProjectRole
from app.models import User
from tests.factories import create_document, create_project, create_project_member, create_user


# Step 1: Create a specific user in the database session
def test_rollback_isolation_step_one(db_session: Session) -> None:
    user = create_user(db_session, login="unique_rollback_user")
    assert user.id is not None

    found = db_session.scalar(select(User).where(User.login == "unique_rollback_user"))
    assert found is not None


# Step 2: Ensure the user from step 1 was rolled back and is not visible
def test_rollback_isolation_step_two(db_session: Session) -> None:
    found = db_session.scalar(select(User).where(User.login == "unique_rollback_user"))
    assert found is None, "Per-test transaction rollback must clean up database changes"


# Check model factories construct interconnected entities cleanly
def test_factories_create_valid_graph(db_session: Session) -> None:
    owner = create_user(db_session, login="owner_user")
    participant = create_user(db_session, login="participant_user")
    project = create_project(db_session, name="Factory Project")

    m_owner = create_project_member(
        db_session,
        project_id=project.id,
        user_id=owner.id,
        role=ProjectRole.OWNER,
    )
    m_participant = create_project_member(
        db_session,
        project_id=project.id,
        user_id=participant.id,
        role=ProjectRole.PARTICIPANT,
    )
    doc = create_document(
        db_session,
        project_id=project.id,
        filename="diagram.png",
        file_size_bytes=2048,
        content_type="image/png",
    )

    db_session.flush()

    assert m_owner.role == ProjectRole.OWNER
    assert m_participant.role == ProjectRole.PARTICIPANT
    assert len(project.members) == 2
    assert len(project.documents) == 1
    assert project.documents[0].id == doc.id


# Check the client fixture serves requests with the transactional test db
def test_client_fixture_with_overridden_db(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
