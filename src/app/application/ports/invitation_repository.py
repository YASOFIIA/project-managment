from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.models.invitation import ProjectInvitation


class InvitationRepository(Protocol):
    """Port for project invitations persistence operations."""

    def create(
        self,
        project_id: int,
        email: str,
        token: str,
        expires_at: datetime,
    ) -> ProjectInvitation:
        """Create and persist a new project invitation."""
        ...

    def get_by_token(self, token: str) -> ProjectInvitation | None:
        """Find project invitation by unique token."""
        ...
