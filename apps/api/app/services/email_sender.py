"""Outbound email.

Development without SMTP appends the message to a local mailbox file. That
file is the captured email. Production with no SMTP host refuses to pretend
the message was delivered. SMTP uses the Python standard library and surfaces
connection errors to the caller.
"""

import json
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import utcnow


@dataclass
class OutboundEmail:
    recipient: str
    subject: str
    body: str
    code: str


class CapturingEmailSender:
    """Test double. Tests read `messages`; nothing is written to disk."""

    def __init__(self) -> None:
        self.messages: list[OutboundEmail] = []

    def send(self, message: OutboundEmail) -> None:
        self.messages.append(message)


class FileMailboxSender:
    def __init__(self, path: Path) -> None:
        self.path = path

    def send(self, message: OutboundEmail) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "recipient": message.recipient,
            "subject": message.subject,
            "body": message.body,
            "code": message.code,
            "created_at": utcnow().isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: OutboundEmail) -> None:
        if not self.settings.smtp_host:
            raise AppError(503, "email_not_configured", "Email delivery is not configured.")
        email = EmailMessage()
        email["From"] = self.settings.smtp_from
        email["To"] = message.recipient
        email["Subject"] = message.subject
        email.set_content(message.body)
        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as smtp:
                if self.settings.smtp_tls:
                    smtp.starttls()
                if self.settings.smtp_username:
                    smtp.login(self.settings.smtp_username, self.settings.smtp_password or "")
                smtp.send_message(email)
        except OSError as exc:
            raise AppError(
                503, "email_delivery_failed", "The verification email could not be sent."
            ) from exc


def build_email_sender(settings: Settings):
    if settings.smtp_host:
        return SmtpEmailSender(settings)
    if settings.app_env == "development":
        return FileMailboxSender(settings.mailbox_file)
    if settings.app_env == "test":
        return CapturingEmailSender()
    raise AppError(
        503,
        "email_not_configured",
        "Production email requires SOLAROPS_SMTP_HOST. The development mailbox is disabled.",
    )


def latest_mailbox_message(path: Path, recipient: str) -> dict | None:
    if not path.exists():
        return None
    found = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("recipient") == recipient:
            found = record
    return found
