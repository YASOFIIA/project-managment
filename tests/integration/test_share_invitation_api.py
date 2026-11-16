from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.domain.roles import ProjectRole
from app.models.invitation import ProjectInvitation
from app.models.project import ProjectMember
from tests.factories import create_project, create_project_member, create_user


# Check project owner can generate share invitation via email
def test_owner_can_share_project(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="owner_share")
    project = create_project(db_session, name="Shareable Workspace")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    headers = {"Authorization": f"Bearer {owner_token}"}

    response = client.get(
        f"/project/{project.id}/share?with=test@example.com",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Invitation sent"
    assert data["email"] == "test@example.com"
    assert data["expires_in_hours"] == 48

    # Verify invitation record in database
    invitation = db_session.scalar(
        select(ProjectInvitation).where(
            ProjectInvitation.project_id == project.id,
            ProjectInvitation.email == "test@example.com",
        )
    )
    assert invitation is not None
    assert invitation.used is False
    assert len(invitation.token) >= 32


# Check participant cannot generate share invitations (403 Forbidden)
def test_participant_cannot_share(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="owner_for_part_share")
    participant = create_user(db_session, login="participant_share")
    project = create_project(db_session, name="Collab Project")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )
    create_project_member(
        db_session, project_id=project.id, user_id=participant.id, role=ProjectRole.PARTICIPANT
    )

    part_token = create_access_token(user_id=participant.id, login=participant.login)
    headers = {"Authorization": f"Bearer {part_token}"}

    response = client.get(
        f"/project/{project.id}/share?with=someone@example.com",
        headers=headers,
    )
    assert response.status_code == 403


# Check non-member receives 404 Not Found to prevent resource enumeration
def test_non_member_cannot_share(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="owner_non_member_share")
    outsider = create_user(db_session, login="outsider_share")
    project = create_project(db_session, name="Private Workspace")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    outsider_token = create_access_token(user_id=outsider.id, login=outsider.login)
    headers = {"Authorization": f"Bearer {outsider_token}"}

    response = client.get(
        f"/project/{project.id}/share?with=someone@example.com",
        headers=headers,
    )
    assert response.status_code == 404


# Check invited user can accept invitation and becomes participant
def test_accept_invitation(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="owner_accept")
    guest = create_user(db_session, login="guest_user")
    project = create_project(db_session, name="Target Project")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    owner_token = create_access_token(user_id=owner.id, login=owner.login)
    share_res = client.get(
        f"/project/{project.id}/share?with=guest@example.com",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert share_res.status_code == 200

    invitation = db_session.scalar(
        select(ProjectInvitation).where(
            ProjectInvitation.project_id == project.id,
            ProjectInvitation.email == "guest@example.com",
        )
    )
    assert invitation is not None

    # Accept invitation as guest
    guest_token = create_access_token(user_id=guest.id, login=guest.login)
    join_res = client.get(
        f"/join?token={invitation.token}",
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert join_res.status_code == 200
    data = join_res.json()
    assert data["project_id"] == project.id
    assert data["user_id"] == guest.id
    assert data["role"] == "participant"

    # Verify membership exists in DB
    membership = db_session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == guest.id,
        )
    )
    assert membership is not None
    assert membership.role == ProjectRole.PARTICIPANT

    # Verify invitation is marked used
    db_session.refresh(invitation)
    assert invitation.used is True


# Check expired invitation token returns 410 Gone
def test_expired_token(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="owner_expired")
    guest = create_user(db_session, login="guest_expired")
    project = create_project(db_session, name="Expired Token Project")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    expired_invitation = ProjectInvitation(
        project_id=project.id,
        email="guest@expired.com",
        token="expired-token-12345",
        created_at=datetime.now(UTC) - timedelta(hours=50),
        expires_at=datetime.now(UTC) - timedelta(hours=2),
        used=False,
    )
    db_session.add(expired_invitation)
    db_session.commit()

    guest_token = create_access_token(user_id=guest.id, login=guest.login)
    res = client.get(
        f"/join?token={expired_invitation.token}",
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert res.status_code == 410


# Check accepting an already used token returns 404 Not Found
def test_used_token(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="owner_used")
    guest1 = create_user(db_session, login="guest_first")
    guest2 = create_user(db_session, login="guest_second")
    project = create_project(db_session, name="Used Token Project")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    invitation = ProjectInvitation(
        project_id=project.id,
        email="colleagues@example.com",
        token="single-use-token-abc",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=48),
        used=False,
    )
    db_session.add(invitation)
    db_session.commit()

    # First user accepts successfully
    t1 = create_access_token(user_id=guest1.id, login=guest1.login)
    r1 = client.get(
        f"/join?token={invitation.token}",
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert r1.status_code == 200

    # Second user attempts with the same token
    t2 = create_access_token(user_id=guest2.id, login=guest2.login)
    r2 = client.get(
        f"/join?token={invitation.token}",
        headers={"Authorization": f"Bearer {t2}"},
    )
    assert r2.status_code == 404


# Check nonexistent token returns 404 Not Found
def test_invalid_token(client: TestClient, db_session: Session) -> None:
    guest = create_user(db_session, login="guest_invalid_tok")
    guest_token = create_access_token(user_id=guest.id, login=guest.login)

    res = client.get(
        "/join?token=totally-random-and-invalid-token",
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert res.status_code == 404


# Check existing member attempting to accept invitation returns 409 Conflict
def test_already_member_accepts(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="owner_already_member")
    existing_member = create_user(db_session, login="already_in_project")
    project = create_project(db_session, name="Conflict Project")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )
    create_project_member(
        db_session,
        project_id=project.id,
        user_id=existing_member.id,
        role=ProjectRole.PARTICIPANT,
    )

    invitation = ProjectInvitation(
        project_id=project.id,
        email="already@example.com",
        token="duplicate-attempt-token",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=48),
        used=False,
    )
    db_session.add(invitation)
    db_session.commit()

    token = create_access_token(user_id=existing_member.id, login=existing_member.login)
    res = client.get(
        f"/join?token={invitation.token}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409


# Check GET /invitations lists pending invitations for current user's email
def test_list_and_accept_or_decline_pending_invitations(
    client: TestClient, db_session: Session
) -> None:
    owner = create_user(db_session, login="inv_owner", email="inv_owner@example.com")
    invitee = create_user(db_session, login="inv_target", email="target@example.com")
    other = create_user(db_session, login="inv_other", email="other@example.com")
    proj1 = create_project(db_session, name="Project One")
    proj2 = create_project(db_session, name="Project Two")
    create_project_member(db_session, project_id=proj1.id, user_id=owner.id, role=ProjectRole.OWNER)
    create_project_member(db_session, project_id=proj2.id, user_id=owner.id, role=ProjectRole.OWNER)

    owner_headers = {"Authorization": f"Bearer {create_access_token(owner.id, owner.login)}"}
    invitee_headers = {"Authorization": f"Bearer {create_access_token(invitee.id, invitee.login)}"}
    other_headers = {"Authorization": f"Bearer {create_access_token(other.id, other.login)}"}

    # Share both projects with target@example.com
    assert (
        client.get(
            f"/project/{proj1.id}/share?with=target@example.com", headers=owner_headers
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/project/{proj2.id}/share?with=target@example.com", headers=owner_headers
        ).status_code
        == 200
    )

    # Other user sees empty list
    assert client.get("/invitations", headers=other_headers).json() == []

    # Target user sees 2 pending invitations
    pending = client.get("/invitations", headers=invitee_headers).json()
    assert len(pending) == 2
    by_proj = {item["project_id"]: item for item in pending}
    assert by_proj[proj1.id]["project_name"] == "Project One"
    assert by_proj[proj2.id]["project_name"] == "Project Two"

    # Other user cannot accept or decline target's invitation -> 404
    inv1_id = by_proj[proj1.id]["id"]
    inv2_id = by_proj[proj2.id]["id"]
    assert client.post(f"/invitations/{inv1_id}/accept", headers=other_headers).status_code == 404
    assert client.post(f"/invitations/{inv2_id}/decline", headers=other_headers).status_code == 404

    # Target accepts proj1 invitation -> 200
    acc = client.post(f"/invitations/{inv1_id}/accept", headers=invitee_headers)
    assert acc.status_code == 200
    assert acc.json()["project_id"] == proj1.id
    assert acc.json()["role"] == "participant"

    # Target declines proj2 invitation -> 204
    dec = client.post(f"/invitations/{inv2_id}/decline", headers=invitee_headers)
    assert dec.status_code == 204

    # Pending list is now empty
    assert client.get("/invitations", headers=invitee_headers).json() == []
