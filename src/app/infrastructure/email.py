from __future__ import annotations

import asyncio
import concurrent.futures
from email.message import EmailMessage

import aiosmtplib

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger("app.email")


# SMTP email sender (works with MailHog in dev)
class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._from = settings.smtp_from

    # Send invitation HTML email
    def send_invitation(
        self,
        to_email: str,
        project_name: str,
        join_url: str,
    ) -> None:
        if not self._host:
            logger.warning(
                "SMTP_HOST is not configured; skipping email dispatch to %s for project '%s'",
                to_email,
                project_name,
            )
            return

        message = EmailMessage()
        message["From"] = self._from
        message["To"] = to_email
        message["Subject"] = f"Invitation to join project '{project_name}'"

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Project Invitation</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
  <h2>You have been invited!</h2>
  <p>You have been invited to join the project
    <strong>{project_name}</strong> on the Project Management Platform.</p>
  <p style="margin: 24px 0;">
    <a href="{join_url}"
       style="background-color: #0066cc; color: #ffffff; padding: 12px 24px;
              text-decoration: none; border-radius: 4px; display: inline-block;">
      Accept Invitation & Join Project
    </a>
  </p>
  <p>Or copy and paste this link into your browser:</p>
  <p><a href="{join_url}">{join_url}</a></p>
  <p style="color: #666; font-size: 0.9em;">This link will expire in 48 hours.</p>
</body>
</html>"""

        message.set_content(
            f"You have been invited to join the project '{project_name}'.\n\n"
            f"Accept the invitation by opening this URL: {join_url}\n\n"
            "This link will expire in 48 hours."
        )
        message.add_alternative(html_body, subtype="html")

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(
                        asyncio.run,
                        aiosmtplib.send(
                            message,
                            hostname=self._host,
                            port=self._port,
                        ),
                    ).result()
            else:
                asyncio.run(
                    aiosmtplib.send(
                        message,
                        hostname=self._host,
                        port=self._port,
                    )
                )
            logger.info("Invitation email dispatched successfully to %s", to_email)
        except Exception as exc:
            logger.error("Failed to send invitation email to %s: %s", to_email, exc)
            raise
