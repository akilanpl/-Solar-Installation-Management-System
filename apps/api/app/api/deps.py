"""HTTP dependencies: database session, CSRF, and the authenticated user."""

import hmac
from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.rate_limit import RateLimiter
from app.core.security import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, new_token
from app.db.session import get_db
from app.models.identity import User
from app.services.auth_service import assert_roles, user_from_session_token


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_limiter(request: Request) -> RateLimiter:
    return request.app.state.limiter


def get_email_sender(request: Request):
    return request.app.state.email_sender


def client_ip(request: Request) -> str:
    # Arbitrary clients can set forwarding headers. Trust only explicitly
    # configured proxies which sanitize those headers before forwarding.
    peer = request.client.host if request.client else "unknown"
    trusted = request.app.state.settings.trusted_proxy_ips.split(",")
    forwarded = request.headers.get("x-forwarded-for") if peer in trusted else None
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client is None:
        return "unknown"
    return request.client.host


def require_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    settings: Settings = request.app.state.settings
    if origin is not None and origin not in settings.origins:
        raise AppError(403, "csrf_failed", "This origin is not allowed to change data.")
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if (
        not cookie
        or not header
        or len(cookie) != len(header)
        or not hmac.compare_digest(cookie, header)
    ):
        raise AppError(403, "csrf_failed", "Missing or invalid CSRF token.")


def issue_csrf() -> str:
    return new_token()


def current_user(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    return user_from_session_token(db, settings, request.cookies.get(SESSION_COOKIE))


def require_role(*roles: str) -> Callable:
    def _checker(user: User = Depends(current_user)) -> User:
        assert_roles(user, set(roles))
        return user

    return _checker
