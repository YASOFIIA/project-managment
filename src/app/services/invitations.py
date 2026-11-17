from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from app.application.ports.email_sender import EmailSender
from app.application.ports.unit_of_work import UnitOfWork
from app.domain.access_policy import Action
from app.domain.errors import (
    InvalidInvitationError,
    InvitationExpiredError,
    ProjectNotFound,
    UserAlreadyMember,
)
from app.domain.roles import ProjectRole
from app.models.project import ProjectMember
from app.schemas.project import InvitationResponse, PendingInvitationResponse
from app.services.access import get_project_membership, require_project_access

logger = logging.getLogger(__name__)


# Create invitation token and send email with join link
def create_and_send_invitation(
    uow: UnitOfWork,
    email_sender: EmailSender,
    project_id: int,
    owner_id: int,
    email: str,
    base_url: str,
    expire_hours: int = 48,
) -> InvitationResponse:
    require_project_access(
        uow, project_id=project_id, user_id=owner_id, action=Action.INVITE_MEMBER
    )
    project = uow.projects.get_by_id(project_id)
    if project is None:
        raise ProjectNotFound(f"Project {project_id} not found")

    clean_email = email.strip().lower()
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=expire_hours)

    with uow:
        uow.invitations.create(
            project_id=project_id,
            email=clean_email,
            token=token,
            expires_at=expires_at,
        )
        uow.commit()

    join_url = f"{base_url.rstrip('/')}/join?token={token}"
    email_sent = True
    try:
        email_sender.send_invitation(
            to_email=clean_email,
            project_name=project.name,
            join_url=join_url,
        )
    except Exception as exc:
        logger.warning(
            "Failed to send invitation email to %s for project '%s': %s",
            clean_email,
            project.name,
            exc,
        )
        email_sent = False

    return InvitationResponse(
        message="Invitation sent",
        email=clean_email,
        expires_in_hours=expire_hours,
        email_sent=email_sent,
    )


# Accept invitation token and add user as participant
def accept_invitation(
    uow: UnitOfWork,
    token: str,
    user_id: int,
) -> ProjectMember:
    invitation = uow.invitations.get_by_token(token)
    if invitation is None or invitation.used:
        raise InvalidInvitationError("Invalid or already used invitation token")

    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at <= datetime.now(UTC):
        raise InvitationExpiredError("Invitation token has expired")

    existing = get_project_membership(uow, project_id=invitation.project_id, user_id=user_id)
    if existing is not None:
        raise UserAlreadyMember(f"User {user_id} is already a member of this project")

    membership = ProjectMember(
        project_id=invitation.project_id,
        user_id=user_id,
        role=ProjectRole.PARTICIPANT,
    )

    with uow:
        invitation.used = True
        try:
            uow.projects.add_member(membership)
            uow.commit()
        except UserAlreadyMember:
            uow.rollback()
            raise

    return membership


# List pending invitations for a user email
def list_pending_invitations_for_email(
    uow: UnitOfWork,
    email: str,
) -> list[PendingInvitationResponse]:
    invitations = uow.invitations.get_pending_by_email(email.strip().lower())
    result: list[PendingInvitationResponse] = []
    for inv in invitations:
        project = uow.projects.get_by_id(inv.project_id)
        result.append(
            PendingInvitationResponse(
                id=inv.id,
                project_id=inv.project_id,
                project_name=project.name if project else "Unknown",
                email=inv.email,
                created_at=inv.created_at,
                expires_at=inv.expires_at,
            )
        )
    return result


# Accept a pending invitation by ID for the given user
def accept_invitation_by_id(
    uow: UnitOfWork,
    invitation_id: int,
    user_id: int,
    user_email: str,
) -> ProjectMember:
    invitation = uow.invitations.get_by_id(invitation_id)
    if invitation is None or invitation.email.lower() != user_email.strip().lower():
        raise InvalidInvitationError("Invitation not found")
    return accept_invitation(uow=uow, token=invitation.token, user_id=user_id)


# Decline a pending invitation by ID for the given user
def decline_invitation_by_id(
    uow: UnitOfWork,
    invitation_id: int,
    user_email: str,
) -> None:
    invitation = uow.invitations.get_by_id(invitation_id)
    if invitation is None or invitation.email.lower() != user_email.strip().lower():
        raise InvalidInvitationError("Invitation not found")
    with uow:
        invitation.used = True
        uow.commit()
