from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.project import Project, ProjectMember, ProjectRole
from tests.factories import create_project, create_project_member, create_user


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

    # Whitespace-only string name (stripped before min_length check)
    response_whitespace = client.post("/projects", json={"name": "   "}, headers=headers)
    assert response_whitespace.status_code == 422

    # Missing name field
    response_missing = client.post("/projects", json={"description": "No name"}, headers=headers)
    assert response_missing.status_code == 422


def test_get_project_info_for_owner_and_participant(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that both project owner and participant can retrieve project details."""
    owner = create_user(db_session, login="owner_viewer")
    participant = create_user(db_session, login="part_viewer")
    project = create_project(db_session, name="Collaborative Project", description="Details")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    # Owner request
    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    owner_resp = client.get(
        f"/project/{project.id}/info",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner_resp.status_code == 200
    assert owner_resp.json()["name"] == "Collaborative Project"

    # Participant request
    part_token = create_access_token(user_id=participant.id, login=participant.login)
    part_resp = client.get(
        f"/project/{project.id}/info",
        headers={"Authorization": f"Bearer {part_token}"},
    )
    assert part_resp.status_code == 200
    assert part_resp.json()["name"] == "Collaborative Project"


def test_get_project_info_non_member_returns_404(client: TestClient, db_session: Session) -> None:
    """Verify that non-members receive 404 when querying project details."""
    stranger = create_user(db_session, login="stranger_viewer")
    project = create_project(db_session, name="Confidential Board")

    token = create_access_token(user_id=stranger.id, login=stranger.login)
    response = client.get(
        f"/project/{project.id}/info",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_get_project_info_unauthenticated_returns_401(client: TestClient) -> None:
    """Verify that unauthenticated calls to GET /project/<id>/info return 401."""
    response = client.get("/project/1/info")
    assert response.status_code == 401


def test_update_project_info_success_by_owner_and_participant(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that owners and participants can update project name and description."""
    owner = create_user(db_session, login="owner_updater")
    participant = create_user(db_session, login="part_updater")
    project = create_project(db_session, name="Old Name", description="Old Desc")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    # 1. Update by owner
    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    resp1 = client.put(
        f"/project/{project.id}/info",
        json={"name": "Owner Updated Name", "description": "Owner Desc"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["name"] == "Owner Updated Name"
    assert resp1.json()["description"] == "Owner Desc"

    # 2. Update by participant
    part_token = create_access_token(user_id=participant.id, login=participant.login)
    resp2 = client.put(
        f"/project/{project.id}/info",
        json={"name": "Participant Updated Name", "description": "Participant Desc"},
        headers={"Authorization": f"Bearer {part_token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Participant Updated Name"
    assert resp2.json()["description"] == "Participant Desc"


def test_update_project_info_non_member_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that non-members cannot update project info (returns 404)."""
    stranger = create_user(db_session, login="stranger_updater")
    project = create_project(db_session, name="Protected Project")

    token = create_access_token(user_id=stranger.id, login=stranger.login)
    response = client.put(
        f"/project/{project.id}/info",
        json={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_update_project_info_empty_name_returns_422(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that PUT /project/<id>/info with empty name returns 422."""
    owner = create_user(db_session, login="owner_bad_update")
    project = create_project(db_session, name="Valid Name")
    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)

    token = create_access_token(user_id=owner.id, login=owner.login)
    response = client.put(
        f"/project/{project.id}/info",
        json={"name": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422

    # Whitespace-only name
    response_whitespace = client.put(
        f"/project/{project.id}/info",
        json={"name": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_whitespace.status_code == 422


def test_delete_project_success_by_owner(client: TestClient, db_session: Session) -> None:
    """Verify that project owner can delete project, cascading members from database."""
    owner = create_user(db_session, login="owner_deleter")
    participant = create_user(db_session, login="part_in_deleted")
    project = create_project(db_session, name="To Be Deleted")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    token = create_access_token(user_id=owner.id, login=owner.login)
    response = client.delete(
        f"/project/{project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert response.text == ""

    # Verify project is deleted in DB
    assert db_session.get(Project, project.id) is None

    # Verify members are cascade-deleted
    members = db_session.scalars(
        select(ProjectMember).where(ProjectMember.project_id == project.id)
    ).all()
    assert len(members) == 0


def test_delete_project_by_participant_returns_403(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that participants cannot delete a project and receive 403 Forbidden."""
    owner = create_user(db_session, login="owner_safe")
    participant = create_user(db_session, login="part_forbidden_del")
    project = create_project(db_session, name="Safe Project")

    create_project_member(db_session, project.id, owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project.id, participant.id, role=ProjectRole.PARTICIPANT)

    token = create_access_token(user_id=participant.id, login=participant.login)
    response = client.delete(
        f"/project/{project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert "Only project owner can perform this operation" in response.json()["detail"]

    # Verify project still exists
    assert db_session.get(Project, project.id) is not None


def test_delete_project_by_non_member_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that non-members receive 404 when attempting to delete a project."""
    stranger = create_user(db_session, login="stranger_deleter")
    project = create_project(db_session, name="Hidden Project")

    token = create_access_token(user_id=stranger.id, login=stranger.login)
    response = client.delete(
        f"/project/{project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert db_session.get(Project, project.id) is not None


def test_delete_project_nonexistent_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify that deleting a non-existent project returns 404."""
    user = create_user(db_session, login="random_user_del")
    token = create_access_token(user_id=user.id, login=user.login)

    response = client.delete(
        "/project/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_delete_project_unauthenticated_returns_401(client: TestClient) -> None:
    """Verify that unauthenticated DELETE /project/<id> returns 401."""
    response = client.delete("/project/1")
    assert response.status_code == 401
