from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.domain.roles import ProjectRole
from app.models.project import ProjectMember
from tests.factories import create_project, create_project_member, create_user


# Check project owner can successfully invite a user as participant
def test_invite_member_success(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="project_owner")
    invitee = create_user(db_session, login="new_colleague")
    project = create_project(db_session, name="Shared Workspace")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {owner_token}"}

    response = client.post(
        f"/project/{project.id}/invite?user={invitee.login}",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project.id
    assert data["user_id"] == invitee.id
    assert data["role"] == "participant"
    assert "id" in data
    assert "created_at" in data

    # Verify DB state
    membership = db_session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == invitee.id,
        )
    )
    assert membership is not None
    assert membership.role == ProjectRole.PARTICIPANT


# Check a participant cannot invite other members (403 Forbidden)
def test_invite_member_by_participant_forbidden_403(
    client: TestClient, db_session: Session
) -> None:
    owner = create_user(db_session, login="owner_user")
    participant = create_user(db_session, login="participant_user")
    invitee = create_user(db_session, login="third_party_user")
    project = create_project(db_session, name="Private Collab")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )
    create_project_member(
        db_session,
        project_id=project.id,
        user_id=participant.id,
        role=ProjectRole.PARTICIPANT,
    )

    participant_token = create_access_token(user_id=participant.id, login=participant.login)
    headers = {"Authorization": f"Bearer {participant_token}"}

    response = client.post(
        f"/project/{project.id}/invite?user={invitee.login}",
        headers=headers,
    )

    assert response.status_code == 403
    assert "Only project owner can perform this operation" in response.json()["detail"]


# Check a non-member receives 404 (information hiding)
def test_invite_member_by_non_member_returns_404(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="real_owner")
    stranger = create_user(db_session, login="stranger_user")
    invitee = create_user(db_session, login="invitee_user")
    project = create_project(db_session, name="Secret Project")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    stranger_token = create_access_token(user_id=stranger.id, login=stranger.login)
    headers = {"Authorization": f"Bearer {stranger_token}"}

    response = client.post(
        f"/project/{project.id}/invite?user={invitee.login}",
        headers=headers,
    )

    assert response.status_code == 404


# Check attempting to invite to nonexistent project returns 404
def test_invite_member_project_not_found_returns_404(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, login="random_user")
    token = create_access_token(user_id=user.id, login=user.login)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/project/999999/invite?user=someone",
        headers=headers,
    )

    assert response.status_code == 404


# Check attempting to invite a non-existent login returns 404
def test_invite_unknown_user_returns_404(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="project_boss")
    project = create_project(db_session, name="Boss Project")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {owner_token}"}

    response = client.post(
        f"/project/{project.id}/invite?user=ghost_user_999",
        headers=headers,
    )

    assert response.status_code == 404
    assert "User 'ghost_user_999' not found" in response.json()["detail"]


# Check attempting to invite an existing member returns 409 Conflict
def test_invite_already_member_returns_409(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="lead_user")
    colleague = create_user(db_session, login="existing_colleague")
    project = create_project(db_session, name="Team Workspace")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )
    create_project_member(
        db_session,
        project_id=project.id,
        user_id=colleague.id,
        role=ProjectRole.PARTICIPANT,
    )

    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {owner_token}"}

    # 1. Invite existing participant
    response = client.post(
        f"/project/{project.id}/invite?user={colleague.login}",
        headers=headers,
    )
    assert response.status_code == 409
    assert f"User '{colleague.login}' is already a member" in response.json()["detail"]

    # 2. Invite self (owner)
    response_self = client.post(
        f"/project/{project.id}/invite?user={owner.login}",
        headers=headers,
    )
    assert response_self.status_code == 409
    assert f"User '{owner.login}' is already a member" in response_self.json()["detail"]


# Check unauthenticated invite request returns 401
def test_invite_unauthenticated_returns_401(client: TestClient) -> None:
    response = client.post("/project/1/invite?user=anyone")
    assert response.status_code == 401


# Check missing or empty user query parameter returns 422
def test_invite_missing_or_empty_param_returns_422(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="lead_dev")
    project = create_project(db_session, name="Alpha Project")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {owner_token}"}

    # Missing query param
    resp1 = client.post(f"/project/{project.id}/invite", headers=headers)
    assert resp1.status_code == 422

    # Empty query param
    resp2 = client.post(f"/project/{project.id}/invite?user=", headers=headers)
    assert resp2.status_code == 422
