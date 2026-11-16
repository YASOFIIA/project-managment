from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.domain.roles import ProjectRole
from app.models.project import ProjectMember
from tests.factories import create_project, create_project_member, create_user


# Helper for Authorization Bearer header
def _auth_headers(user_id: int, login: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user_id, login=login)}"}


# Members list shows owner and invited participant, hidden from non-members
def test_list_members(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="m_owner")
    guest = create_user(db_session, login="m_guest")
    outsider = create_user(db_session, login="m_outsider")
    project = create_project(db_session)
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )
    create_project_member(
        db_session, project_id=project.id, user_id=guest.id, role=ProjectRole.PARTICIPANT
    )

    ok = client.get(f"/project/{project.id}/members", headers=_auth_headers(owner.id, owner.login))
    assert ok.status_code == 200
    assert {(m["login"], m["role"]) for m in ok.json()} == {
        ("m_owner", "owner"),
        ("m_guest", "participant"),
    }

    hidden = client.get(
        f"/project/{project.id}/members", headers=_auth_headers(outsider.id, outsider.login)
    )
    assert hidden.status_code == 404


# Owner removes a participant -> 204 No Content
def test_owner_removes_participant_returns_204(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="rm_owner")
    participant = create_user(db_session, login="rm_participant")
    project = create_project(db_session, name="Removable Team")
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )
    part_member = create_project_member(
        db_session, project_id=project.id, user_id=participant.id, role=ProjectRole.PARTICIPANT
    )

    resp = client.delete(
        f"/project/{project.id}/members/{part_member.id}",
        headers=_auth_headers(owner.id, owner.login),
    )
    assert resp.status_code == 204

    remaining = db_session.scalar(select(ProjectMember).where(ProjectMember.id == part_member.id))
    assert remaining is None


# Participant tries to remove a member -> 403 Forbidden
def test_participant_cannot_remove_member_returns_403(
    client: TestClient, db_session: Session
) -> None:
    owner = create_user(db_session, login="p_owner")
    part1 = create_user(db_session, login="p_one")
    part2 = create_user(db_session, login="p_two")
    project = create_project(db_session)
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )
    create_project_member(
        db_session, project_id=project.id, user_id=part1.id, role=ProjectRole.PARTICIPANT
    )
    m2 = create_project_member(
        db_session, project_id=project.id, user_id=part2.id, role=ProjectRole.PARTICIPANT
    )

    resp = client.delete(
        f"/project/{project.id}/members/{m2.id}",
        headers=_auth_headers(part1.id, part1.login),
    )
    assert resp.status_code == 403


# Owner tries to remove self -> 403 Forbidden
def test_owner_cannot_remove_self_returns_403(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="self_owner")
    project = create_project(db_session)
    owner_member = create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    resp = client.delete(
        f"/project/{project.id}/members/{owner_member.id}",
        headers=_auth_headers(owner.id, owner.login),
    )
    assert resp.status_code == 403
    assert "Cannot remove yourself" in resp.json()["detail"]


# Owner tries to remove another owner -> 403 Forbidden
def test_owner_cannot_remove_another_owner_returns_403(
    client: TestClient, db_session: Session
) -> None:
    owner1 = create_user(db_session, login="co_owner_1")
    owner2 = create_user(db_session, login="co_owner_2")
    project = create_project(db_session)
    create_project_member(
        db_session, project_id=project.id, user_id=owner1.id, role=ProjectRole.OWNER
    )
    owner2_member = create_project_member(
        db_session, project_id=project.id, user_id=owner2.id, role=ProjectRole.OWNER
    )

    resp = client.delete(
        f"/project/{project.id}/members/{owner2_member.id}",
        headers=_auth_headers(owner1.id, owner1.login),
    )
    assert resp.status_code == 403
    assert "Cannot remove a project owner" in resp.json()["detail"]


# Remove non-existent member -> 404 Not Found
def test_remove_nonexistent_member_returns_404(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, login="nf_owner")
    project = create_project(db_session)
    create_project_member(
        db_session, project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER
    )

    resp = client.delete(
        f"/project/{project.id}/members/999999",
        headers=_auth_headers(owner.id, owner.login),
    )
    assert resp.status_code == 404
