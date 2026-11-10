from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.project import ProjectRole
from tests.factories import create_project_member, create_user


def test_two_users_collaboration_and_access_lifecycle(
    client: TestClient,
    db_session: Session,
) -> None:
    """Verify Phase 3 'Done when' criterion:

    - Two users.
    - Projects visible only to members.
    - Non-member receives 404 (information hiding).
    - Participant can view and edit, but receives 403 Forbidden on delete.
    - Owner can delete (204 No Content).
    """
    # 1. Register and login User A (Project Creator / Owner)
    reg_a = client.post(
        "/auth",
        json={"login": "alice", "password": "password123", "repeat_password": "password123"},
    )
    assert reg_a.status_code == 201

    login_a = client.post("/login", json={"login": "alice", "password": "password123"})
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register and login User B (Collaborator / Participant)
    reg_b = client.post(
        "/auth",
        json={"login": "bob_collab", "password": "password123", "repeat_password": "password123"},
    )
    assert reg_b.status_code == 201
    user_b_id = reg_b.json()["id"]

    login_b = client.post("/login", json={"login": "bob_collab", "password": "password123"})
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A creates a project (201 Created)
    proj_resp = client.post(
        "/projects",
        json={"name": "Alice Secret Project", "description": "Top secret work."},
        headers=headers_a,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 4. User B cannot see Alice's project (GET /projects returns empty list)
    b_projects = client.get("/projects", headers=headers_b)
    assert b_projects.status_code == 200
    assert len(b_projects.json()) == 0

    # 5. User B receives 404 on direct access (Information Hiding)
    assert client.get(f"/project/{project_id}/info", headers=headers_b).status_code == 404
    assert (
        client.put(
            f"/project/{project_id}/info",
            json={"name": "Hijacked"},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert client.delete(f"/project/{project_id}", headers=headers_b).status_code == 404

    # 6. User B is added as PARTICIPANT
    create_project_member(
        db_session,
        project_id=project_id,
        user_id=user_b_id,
        role=ProjectRole.PARTICIPANT,
    )

    # 7. User B can now see the project in the listing
    b_projects_after = client.get("/projects", headers=headers_b)
    assert b_projects_after.status_code == 200
    assert len(b_projects_after.json()) == 1
    assert b_projects_after.json()[0]["id"] == project_id
    assert b_projects_after.json()[0]["name"] == "Alice Secret Project"

    # 8. User B can view and update project info (200 OK)
    b_info = client.get(f"/project/{project_id}/info", headers=headers_b)
    assert b_info.status_code == 200
    assert b_info.json()["name"] == "Alice Secret Project"

    b_update = client.put(
        f"/project/{project_id}/info",
        json={"name": "Collaborative Alpha", "description": "Updated together."},
        headers=headers_b,
    )
    assert b_update.status_code == 200
    assert b_update.json()["name"] == "Collaborative Alpha"

    # 9. User B tries to delete the project -> 403 Forbidden
    b_delete = client.delete(f"/project/{project_id}", headers=headers_b)
    assert b_delete.status_code == 403
    assert "Only project owner can perform this operation" in b_delete.json()["detail"]

    # 10. User A (Owner) successfully deletes the project -> 204 No Content
    a_delete = client.delete(f"/project/{project_id}", headers=headers_a)
    assert a_delete.status_code == 204
    assert a_delete.text == ""

    # 11. Project is gone for both users -> 404 Not Found
    assert client.get(f"/project/{project_id}/info", headers=headers_a).status_code == 404
    assert client.get(f"/project/{project_id}/info", headers=headers_b).status_code == 404


def test_api_status_codes_matrix(client: TestClient, db_session: Session) -> None:
    """Explicitly verify every required HTTP status code across the API:

    - 200 OK
    - 201 Created
    - 204 No Content
    - 401 Unauthorized
    - 403 Forbidden
    - 404 Not Found
    - 422 Unprocessable Entity
    """
    # 201 Created: Registration & Project creation
    reg_res = client.post(
        "/auth",
        json={
            "login": "status_tester",
            "password": "password123",
            "repeat_password": "password123",
        },
    )
    assert reg_res.status_code == 201

    # 200 OK: Login
    login_res = client.post("/login", json={"login": "status_tester", "password": "password123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 200 OK: /health and /auth/me
    assert client.get("/health").status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 200

    # 201 Created: Project creation
    create_res = client.post("/projects", json={"name": "Status Project"}, headers=headers)
    assert create_res.status_code == 201
    proj_id = create_res.json()["id"]

    # 200 OK: Project list, Project info, Project update
    assert client.get("/projects", headers=headers).status_code == 200
    assert client.get(f"/project/{proj_id}/info", headers=headers).status_code == 200
    assert (
        client.put(
            f"/project/{proj_id}/info",
            json={"name": "Updated Status Project"},
            headers=headers,
        ).status_code
        == 200
    )

    # 401 Unauthorized: missing or invalid credentials
    assert client.get("/projects").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer bad_token"}).status_code == 401
    assert (
        client.post(
            "/login",
            json={"login": "status_tester", "password": "wrong_password"},
        ).status_code
        == 401
    )

    # 403 Forbidden: participant attempting owner-only action
    part_user = create_user(db_session, login="part_status_user")
    participant_token = create_access_token(user_id=part_user.id, login=part_user.login)
    create_project_member(
        db_session,
        project_id=proj_id,
        user_id=part_user.id,
        role=ProjectRole.PARTICIPANT,
    )
    assert (
        client.delete(
            f"/project/{proj_id}",
            headers={"Authorization": f"Bearer {participant_token}"},
        ).status_code
        == 403
    )

    # 404 Not Found: non-existent endpoint, resource, or unauthorized access
    assert client.get("/non_existent_route").status_code == 404
    assert client.get("/project/88888/info", headers=headers).status_code == 404
    assert client.delete("/project/88888", headers=headers).status_code == 404

    # 422 Unprocessable Entity: validation error (empty string / malformed JSON)
    assert client.post("/projects", json={"name": ""}, headers=headers).status_code == 422
    assert (
        client.post(
            "/auth",
            json={"login": "", "password": "123", "repeat_password": "mismatch"},
        ).status_code
        == 422
    )

    # 204 No Content: Successful deletion
    delete_res = client.delete(f"/project/{proj_id}", headers=headers)
    assert delete_res.status_code == 204
    assert delete_res.text == ""
