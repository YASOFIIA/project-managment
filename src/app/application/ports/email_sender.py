from __future__ import annotations

from typing import Protocol


# Email sender port
class EmailSender(Protocol):
    # Send invitation email with join URL
    def send_invitation(
        self,
        to_email: str,
        project_name: str,
        join_url: str,
    ) -> None: ...
