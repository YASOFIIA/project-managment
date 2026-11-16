from __future__ import annotations

from datetime import datetime

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
