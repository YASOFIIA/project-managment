from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.models.invitation import ProjectInvitation


# Invitation repository port
class InvitationRepository(Protocol):
    # Create and save project invitation
    def create(
        self,
        project_id: int,
        email: str,
        token: str,
        expires_at: datetime,
    ) -> ProjectInvitation: ...

    # Find invitation by token
    def get_by_token(self, token: str) -> ProjectInvitation | None: ...

    # Find invitation by ID
    def get_by_id(self, invitation_id: int) -> ProjectInvitation | None: ...

    # Find pending (unused, non-expired) invitations for email
    def get_pending_by_email(self, email: str) -> list[ProjectInvitation]: ...
