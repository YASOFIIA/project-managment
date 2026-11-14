from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invitation import ProjectInvitation


class SqlAlchemyInvitationRepository:
    """SQLAlchemy adapter for ProjectInvitation persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        project_id: int,
        email: str,
        token: str,
        expires_at: datetime,
    ) -> ProjectInvitation:
        """Create and persist a new project invitation."""
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

    def get_by_token(self, token: str) -> ProjectInvitation | None:
        """Find project invitation by unique token."""
        stmt = select(ProjectInvitation).where(ProjectInvitation.token == token)
        return self._session.scalars(stmt).first()
