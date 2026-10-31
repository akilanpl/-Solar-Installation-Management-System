from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.core.config import Settings
from app.core.errors import AppError
from app.schemas import DevMailboxMessage
from app.services.email_sender import latest_mailbox_message

router = APIRouter(prefix="/dev", tags=["development"])


@router.get("/mailbox/{email}", response_model=DevMailboxMessage)
def read_mailbox(email: str, settings: Settings = Depends(get_settings)):
    """Development-only captured email.

    Returns 404 unless the API is running with SOLAROPS_APP_ENV=development
    and SMTP is not configured. The code in the response is the message that
    was written to the local mailbox file. It is not read back out of the
    password or challenge tables.
    """

    if not settings.development_mailbox_enabled:
        raise AppError(404, "not_found", "Not found.")
    record = latest_mailbox_message(settings.mailbox_file, email.lower())
    if record is None:
        raise AppError(404, "not_found", "No captured email for that address.")
    return DevMailboxMessage(
        recipient=record["recipient"],
        subject=record["subject"],
        body=record["body"],
        code=record["code"],
        created_at=record["created_at"],
    )
