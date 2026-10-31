"""Password hashing, session token hashing, and one-time codes.

Argon2id parameters are explicit so a reviewer can see the cost. Session
tokens and OTP codes are stored only as HMAC-SHA256 digests keyed by the
server secret. A database copy alone does not reveal the cookie or the code.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.low_level import Type

_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# Used when the account does not exist so unknown users still pay Argon2 time.
DUMMY_PASSWORD_HASH = _hasher.hash("solarops-not-a-user-password")

SESSION_COOKIE = "solarops_session"
CSRF_COOKIE = "solarops_csrf"
CSRF_HEADER = "x-csrf-token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def dummy_password_check(password: str) -> None:
    verify_password(DUMMY_PASSWORD_HASH, password)


def hash_secret(raw: str, pepper: str) -> str:
    return hmac.new(pepper.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def secrets_match(stored_hex: str, raw: str, pepper: str) -> bool:
    return hmac.compare_digest(stored_hex, hash_secret(raw, pepper))


def new_token() -> str:
    return secrets.token_urlsafe(32)


def new_otp() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


def utcnow() -> datetime:
    return datetime.now(UTC)


def expiry_from_now(*, hours: int = 0, minutes: int = 0) -> datetime:
    return utcnow() + timedelta(hours=hours, minutes=minutes)
