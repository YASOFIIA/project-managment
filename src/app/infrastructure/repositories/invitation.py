from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invitation import ProjectInvitation


# SQLAlchemy adapter for project invitations
class SqlAlchemyInvitationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # Create and save project invitation
    def create(
        self,
        project_id: int,
        email: str,
        token: str,
        expires_at: datetime,
    ) -> ProjectInvitation:
        invitation = ProjectInvitation(
            project_id=project_id,
            email=email,
            token=token,
            expires_at=expires_at,
            used=False,
        )
        self._session.add(invitation)
        self._session.flush()
        return invitation

    # Find invitation by token
    def get_by_token(self, token: str) -> ProjectInvitation | None:
        stmt = select(ProjectInvitation).where(ProjectInvitation.token == token)
        return self._session.scalars(stmt).first()

    # Find invitation by ID
    def get_by_id(self, invitation_id: int) -> ProjectInvitation | None:
        return self._session.get(ProjectInvitation, invitation_id)

    # Find pending (unused, non-expired) invitations for email
    def get_pending_by_email(self, email: str) -> list[ProjectInvitation]:
        now = datetime.now(UTC)
        stmt = (
            select(ProjectInvitation)
            .where(
                ProjectInvitation.email == email,
                ProjectInvitation.used.is_(False),
                ProjectInvitation.expires_at > now,
            )
            .order_by(ProjectInvitation.created_at.desc())
        )
        return list(self._session.scalars(stmt).all())
