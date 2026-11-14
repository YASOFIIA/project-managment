from __future__ import annotations

from typing import Protocol


class EmailSender(Protocol):
    """Port for dispatching transactional notification emails."""

    def send_invitation(
        self,
        to_email: str,
        project_name: str,
        join_url: str,
    ) -> None:
        """Send project invitation email containing join URL to recipient."""
        ...
