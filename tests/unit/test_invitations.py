from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.application.ports.email_sender import EmailSender
from app.application.ports.unit_of_work import UnitOfWork
from app.core.config import Settings
from app.domain.errors import (
    InvalidInvitationError,
    InvitationExpiredError,
    PermissionDenied,
    ProjectNotFound,
    UserAlreadyMember,
)
from app.domain.roles import ProjectRole
from app.infrastructure.email import SmtpEmailSender
from app.models.invitation import ProjectInvitation
from app.models.project import Project, ProjectMember
from app.services.invitations import accept_invitation, create_and_send_invitation


# Check owner can generate invitation token and dispatch email
def test_create_and_send_invitation_success() -> None:
    mock_uow = MagicMock(spec=UnitOfWork)
    mock_email_sender = MagicMock(spec=EmailSender)

    # Owner membership and project exist
    owner_member = ProjectMember(project_id=1, user_id=10, role=ProjectRole.OWNER)
    mock_uow.projects.get_membership.return_value = owner_member
    mock_uow.projects.get_by_id.return_value = Project(id=1, name="Apollo")

    resp = create_and_send_invitation(
        uow=mock_uow,
        email_sender=mock_email_sender,
        project_id=1,
        owner_id=10,
        email="bob@example.com",
        base_url="http://localhost:8000",
        expire_hours=48,
    )

    assert resp.message == "Invitation sent"
    assert resp.email == "bob@example.com"
    assert resp.expires_in_hours == 48

    mock_uow.invitations.create.assert_called_once()
    mock_uow.commit.assert_called_once()
    mock_email_sender.send_invitation.assert_called_once()
    args, kwargs = mock_email_sender.send_invitation.call_args
    assert kwargs["to_email"] == "bob@example.com"
    assert kwargs["project_name"] == "Apollo"
    assert "/join?token=" in kwargs["join_url"]


# Check participant cannot generate share invitations
def test_create_and_send_invitation_participant_forbidden() -> None:
    mock_uow = MagicMock(spec=UnitOfWork)
    mock_email_sender = MagicMock(spec=EmailSender)

    participant_member = ProjectMember(project_id=1, user_id=20, role=ProjectRole.PARTICIPANT)
    mock_uow.projects.get_membership.return_value = participant_member

    with pytest.raises(PermissionDenied):
        create_and_send_invitation(
            uow=mock_uow,
            email_sender=mock_email_sender,
            project_id=1,
            owner_id=20,
            email="colleague@example.com",
            base_url="http://localhost:8000",
        )


# Check ProjectNotFound when project entity does not exist
def test_create_and_send_invitation_project_not_found() -> None:
    mock_uow = MagicMock(spec=UnitOfWork)
    mock_email_sender = MagicMock(spec=EmailSender)

    owner_member = ProjectMember(project_id=99, user_id=10, role=ProjectRole.OWNER)
    mock_uow.projects.get_membership.return_value = owner_member
    mock_uow.projects.get_by_id.return_value = None

    with pytest.raises(ProjectNotFound):
        create_and_send_invitation(
            uow=mock_uow,
            email_sender=mock_email_sender,
            project_id=99,
            owner_id=10,
            email="colleague@example.com",
            base_url="http://localhost:8000",
        )


# Check valid token adds user as participant and marks invitation used
def test_accept_invitation_success() -> None:
    mock_uow = MagicMock(spec=UnitOfWork)
    invitation = ProjectInvitation(
        id=1,
        project_id=100,
        email="guest@example.com",
        token="valid-token-123",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        used=False,
    )
    mock_uow.invitations.get_by_token.return_value = invitation
    mock_uow.projects.get_membership.return_value = None

    created_member = ProjectMember(project_id=100, user_id=5, role=ProjectRole.PARTICIPANT)
    mock_uow.projects.add_member.return_value = created_member

    member = accept_invitation(
        uow=mock_uow,
        token="valid-token-123",
        user_id=5,
    )

    assert member.user_id == 5
    assert member.project_id == 100
    assert member.role == ProjectRole.PARTICIPANT
    assert invitation.used is True
    mock_uow.commit.assert_called_once()


# Check InvalidInvitationError for nonexistent or already used tokens
def test_accept_invitation_invalid_or_used() -> None:
    mock_uow = MagicMock(spec=UnitOfWork)
    mock_uow.invitations.get_by_token.return_value = None

    with pytest.raises(InvalidInvitationError):
        accept_invitation(mock_uow, token="nonexistent", user_id=5)

    used_invitation = ProjectInvitation(
        id=2,
        project_id=100,
        email="guest@example.com",
        token="used-token",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        used=True,
    )
    mock_uow.invitations.get_by_token.return_value = used_invitation

    with pytest.raises(InvalidInvitationError):
        accept_invitation(mock_uow, token="used-token", user_id=5)


# Check InvitationExpiredError when expiration timestamp is in the past
def test_accept_invitation_expired() -> None:
    mock_uow = MagicMock(spec=UnitOfWork)
    expired_invitation = ProjectInvitation(
        id=3,
        project_id=100,
        email="guest@example.com",
        token="expired-token",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        used=False,
    )
    mock_uow.invitations.get_by_token.return_value = expired_invitation

    with pytest.raises(InvitationExpiredError):
        accept_invitation(mock_uow, token="expired-token", user_id=5)


# Check UserAlreadyMember when user is already a project collaborator
def test_accept_invitation_already_member() -> None:
    mock_uow = MagicMock(spec=UnitOfWork)
    invitation = ProjectInvitation(
        id=4,
        project_id=100,
        email="member@example.com",
        token="token-4",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        used=False,
    )
    mock_uow.invitations.get_by_token.return_value = invitation
    mock_uow.projects.get_membership.return_value = ProjectMember(
        project_id=100, user_id=7, role=ProjectRole.PARTICIPANT
    )

    with pytest.raises(UserAlreadyMember):
        accept_invitation(mock_uow, token="token-4", user_id=7)


# Check SmtpEmailSender skips dispatch without errors when smtp_host is empty
def test_smtp_email_sender_graceful_degradation_without_host() -> None:
    settings = Settings(
        jwt_secret_key="secret",
        lambda_callback_secret="secret",
        smtp_host="",
    )
    sender = SmtpEmailSender(settings)
    # Must execute cleanly without exception
    sender.send_invitation(
        to_email="test@example.com",
        project_name="Demo",
        join_url="http://localhost:8000/join?token=abc",
    )
