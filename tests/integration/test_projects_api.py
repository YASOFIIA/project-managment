from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.project import Project, ProjectMember, ProjectRole
from tests.factories import create_user


def test_create_project_success(client: TestClient, db_session: Session) -> None:
    """Verify that POST /projects creates a project and makes the user the owner."""
    user = create_user(db_session, login="project_creator")
    token = create_access_token(user_id=user.id, login=user.login)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Super AI Platform",
        "description": "Building next-generation intelligent agents.",
    }

    response = client.post("/projects", json=payload, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Super AI Platform"
    assert data["description"] == "Building next-generation intelligent agents."
    assert data["total_size_bytes"] == 0
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    project_id = data["id"]

    # Verify atomic database state
    db_project = db_session.get(Project, project_id)
    assert db_project is not None
    assert db_project.name == "Super AI Platform"

    membership = db_session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    assert membership is not None
    assert membership.role == ProjectRole.OWNER


def test_create_project_unauthenticated_returns_401(client: TestClient) -> None:
    """Verify that unauthenticated POST /projects requests are rejected with 401."""
    payload = {"name": "Unauthorized Project"}
    response = client.post("/projects", json=payload)

    assert response.status_code == 401


def test_create_project_empty_name_returns_422(client: TestClient, db_session: Session) -> None:
    """Verify that creating a project with an empty or missing name returns 422."""
    user = create_user(db_session, login="valid_user")
    token = create_access_token(user_id=user.id, login=user.login)
    headers = {"Authorization": f"Bearer {token}"}

    # Empty string name
    response = client.post("/projects", json={"name": ""}, headers=headers)
    assert response.status_code == 422

    # Missing name field
    response_missing = client.post("/projects", json={"description": "No name"}, headers=headers)
    assert response_missing.status_code == 422
