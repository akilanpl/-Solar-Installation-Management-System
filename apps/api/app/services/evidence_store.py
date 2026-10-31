"""Local survey evidence files.

The storage key is a generated id, never a client path. Retrieval reads only
that key from the configured directory.
"""

import uuid
from pathlib import Path

from app.core.config import Settings
from app.core.errors import AppError

_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF-", "application/pdf"),
)


def sniff_content_type(payload: bytes) -> str | None:
    for signature, content_type in _SIGNATURES:
        if payload.startswith(signature):
            return content_type
    if len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "image/webp"
    return None


def save_evidence(settings: Settings, payload: bytes) -> tuple[str, str]:
    if not payload:
        raise AppError(422, "validation_error", "The evidence file is empty.")
    if len(payload) > settings.evidence_max_bytes:
        raise AppError(413, "file_too_large", "Survey evidence must be 5 MB or smaller.")
    content_type = sniff_content_type(payload)
    if content_type is None:
        raise AppError(
            422,
            "validation_error",
            "Survey evidence must be a JPEG, PNG, WebP, or PDF file.",
        )
    directory = settings.evidence_path
    directory.mkdir(parents=True, exist_ok=True)
    key = uuid.uuid4().hex
    target = directory / key
    target.write_bytes(payload)
    return key, content_type


def evidence_file(settings: Settings, storage_key: str) -> Path:
    if len(storage_key) != 32 or any(char not in "0123456789abcdef" for char in storage_key):
        raise AppError(404, "not_found", "Evidence not found.")
    path = settings.evidence_path / storage_key
    if not path.is_file():
        raise AppError(404, "not_found", "Evidence not found.")
    return path
