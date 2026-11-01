"""Phase 4E authentication routes: passkeys, TOTP MFA, step-up verification.

Password login keeps working exactly as before. When the account has a
verified second factor, password login stops at a short-lived MFA ticket
(HTTP 202) instead of a session; the ticket is redeemed with a TOTP code or
recovery code. Passkey assertion is a complete login in one step because a
user-verified passkey is phishing-resistant authenticator strength.
"""

import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.cookies import set_csrf_cookie, set_session_cookie
from app.api.deps import client_ip, current_user, get_limiter, get_settings, issue_csrf
from app.core.config import Settings
from app.core.errors import AppError
from app.core.rate_limit import RateLimiter
from app.core.security import SESSION_COOKIE, verify_password
from app.db.session import get_db as get_db_dep
from app.models.identity import User
from app.schemas import (
    LoginResponse,
    MfaStatusResponse,
    MfaTicketVerifyRequest,
    PasskeyCredentialResponse,
    PasskeyOptionsResponse,
    PasskeyVerifyLoginRequest,
    PasskeyVerifyRequest,
    RecoveryCodesResponse,
    RevokeRequest,
    StepUpPasskeyRequest,
    StepUpStartResponse,
    StrongGrantResponse,
    TotpEnrollStartRequest,
    TotpEnrollStartResponse,
    TotpVerifyRequest,
)
from app.services import auth_service, mfa_service, webauthn_service
from app.services.auth_service import user_from_session_token

router = APIRouter(prefix="/auth", tags=["auth-4e"])

STRONG_AUTH_HEADER = "X-Strong-Auth"


def _optional_user(request: Request, db: Session, settings: Settings) -> User | None:
    try:
        return user_from_session_token(db, settings, request.cookies.get(SESSION_COOKIE))
    except AppError:
        return None


def _password_confirmed(user: User, password: str) -> None:
    if not verify_password(user.password_hash, password):
        raise AppError(401, "invalid_credentials", "The password is incorrect.")


def _reauthenticated(
    request: Request, db: Session, settings: Settings, user: User, password: str | None
) -> None:
    """Sensitive account changes need a fresh proof: grant header or password."""
    grant = request.headers.get(STRONG_AUTH_HEADER)
    if grant:
        mfa_service.consume_strong_grant(db, settings, user, grant, used_for=request.url.path)
        return
    if password:
        _password_confirmed(user, password)
        return
    raise AppError(403, "strong_auth_required", "Reauthenticate to continue.")


def _credential_response(row) -> PasskeyCredentialResponse:
    return PasskeyCredentialResponse(
        id=row.id,
        credential_id=row.credential_id_b64,
        label=row.label,
        backed_up=row.backed_up,
        sign_count=row.sign_count,
        created_at=row.created_at,
    )


def _strong_methods(db: Session, user: User) -> list[str]:
    return mfa_service.available_step_up_methods(db, user)


# ---------------------------------------------------------------- passkeys

@router.post("/passkeys/registration/options", response_model=PasskeyOptionsResponse)
def passkey_registration_options(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> PasskeyOptionsResponse:
    limiter.check(
        f"webauthn-options:{user.id}", limit=20, window_seconds=settings.rate_limit_window_seconds
    )
    return PasskeyOptionsResponse(options=webauthn_service.registration_options(db, settings, user))


@router.post("/passkeys/registration/verify", response_model=PasskeyCredentialResponse,
             status_code=201)
def passkey_registration_verify(
    payload: PasskeyVerifyRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> PasskeyCredentialResponse:
    limiter.check(
        f"webauthn-verify:{user.id}", limit=20, window_seconds=settings.rate_limit_window_seconds
    )
    stored = webauthn_service.verify_registration(
        db, settings, user, payload.credential, payload.label.strip() or "Passkey"
    )
    return _credential_response(stored)


@router.get("/passkeys", response_model=list[PasskeyCredentialResponse])
def list_passkeys(
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
) -> list[PasskeyCredentialResponse]:
    return [_credential_response(row) for row in webauthn_service.list_credentials(db, user)]


@router.post("/passkeys/authentication/options", response_model=PasskeyOptionsResponse)
def passkey_authentication_options(
    request: Request,
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> PasskeyOptionsResponse:
    limiter.check(
        f"webauthn-auth-options:{client_ip(request)}",
        limit=30, window_seconds=settings.rate_limit_window_seconds,
    )
    scoped = _optional_user(request, db, settings)
    return PasskeyOptionsResponse(
        options=webauthn_service.authentication_options(db, settings, scoped)
    )


@router.post("/passkeys/authentication/verify", response_model=LoginResponse)
def passkey_authentication_verify(
    payload: PasskeyVerifyLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> LoginResponse:
    limiter.check(
        f"webauthn-auth:{client_ip(request)}",
        limit=settings.login_ip_limit, window_seconds=settings.rate_limit_window_seconds,
    )
    owner, _ = webauthn_service.verify_authentication(db, settings, payload.credential)
    raw = auth_service.create_session(
        db, settings, owner,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
        action="user.login",
        metadata={"method": "passkey"},
    )
    set_session_cookie(response, settings, raw)
    set_csrf_cookie(response, settings, issue_csrf())
    return LoginResponse(user=auth_service.to_current_user(owner))


@router.post("/passkeys/{credential_id}/revoke", response_model=PasskeyCredentialResponse)
def revoke_passkey(
    credential_id: uuid.UUID,
    payload: RevokeRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
) -> PasskeyCredentialResponse:
    _reauthenticated(request, db, settings, user, payload.password)
    stored = webauthn_service.revoke_credential(db, user, credential_id)
    return _credential_response(stored)


# ---------------------------------------------------------------- MFA status

@router.get("/mfa/status", response_model=MfaStatusResponse)
def mfa_status(
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
) -> MfaStatusResponse:
    methods = mfa_service.user_mfa_methods(db, user)
    return MfaStatusResponse(**methods)


# ---------------------------------------------------------------- TOTP enrollment

@router.post("/mfa/totp/enroll/start", response_model=TotpEnrollStartResponse)
def totp_enroll_start(
    payload: TotpEnrollStartRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> TotpEnrollStartResponse:
    limiter.check(
        f"mfa-enroll:{user.id}", limit=8, window_seconds=settings.rate_limit_window_seconds
    )
    _password_confirmed(user, payload.password)
    factor, uri = mfa_service.start_totp_enrollment(db, settings, user, payload.label.strip())
    return TotpEnrollStartResponse(factor_id=factor.id, otpauth_uri=uri)


@router.post("/mfa/totp/enroll/confirm", response_model=MfaStatusResponse)
def totp_enroll_confirm(
    payload: TotpVerifyRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> MfaStatusResponse:
    limiter.check(
        f"mfa-verify:{user.id}", limit=settings.otp_attempt_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    mfa_service.confirm_totp_enrollment(db, settings, user, payload.code)
    return MfaStatusResponse(**mfa_service.user_mfa_methods(db, user))


# ---------------------------------------------------------------- MFA ticket redemption (login)

def _issue_session(
    request: Request, response: Response, settings: Settings, db: Session, user: User,
    method: str,
) -> LoginResponse:
    raw = auth_service.create_session(
        db, settings, user,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
        action="user.login",
        metadata={"method": method},
    )
    set_session_cookie(response, settings, raw)
    set_csrf_cookie(response, settings, issue_csrf())
    return LoginResponse(user=auth_service.to_current_user(user))


@router.post("/mfa/ticket/verify-totp", response_model=LoginResponse)
def ticket_verify_totp(
    payload: MfaTicketVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> LoginResponse:
    limiter.check(
        f"mfa-ticket:{client_ip(request)}", limit=settings.otp_attempt_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    user = mfa_service.verify_ticket_totp(db, settings, payload.ticket, "login", payload.code)
    return _issue_session(request, response, settings, db, user, "totp")


@router.post("/mfa/ticket/verify-recovery", response_model=LoginResponse)
def ticket_verify_recovery(
    payload: MfaTicketVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> LoginResponse:
    limiter.check(
        f"mfa-ticket:{client_ip(request)}", limit=settings.otp_attempt_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    user = mfa_service.verify_ticket_recovery(db, settings, payload.ticket, "login", payload.code)
    mfa_service.revoke_all_sessions(db, user)
    return _issue_session(request, response, settings, db, user, "recovery_code")


# ---------------------------------------------------------------- recovery codes

@router.post("/mfa/recovery-codes", response_model=RecoveryCodesResponse, status_code=201)
def issue_recovery_codes(
    payload: TotpEnrollStartRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> RecoveryCodesResponse:
    limiter.check(
        f"mfa-recovery:{user.id}", limit=5, window_seconds=settings.rate_limit_window_seconds
    )
    _password_confirmed(user, payload.password)
    codes = mfa_service.issue_recovery_codes(db, settings, user)
    return RecoveryCodesResponse(codes=codes)


@router.post("/mfa/factors/{factor_id}/revoke", response_model=MfaStatusResponse)
def revoke_factor(
    factor_id: uuid.UUID,
    payload: RevokeRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
) -> MfaStatusResponse:
    _reauthenticated(request, db, settings, user, payload.password)
    mfa_service.revoke_factor(db, user, factor_id)
    return MfaStatusResponse(**mfa_service.user_mfa_methods(db, user))


# ---------------------------------------------------------------- step-up and revocation

@router.post("/step-up/start", response_model=StepUpStartResponse)
def step_up_start(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> StepUpStartResponse:
    limiter.check(
        f"step-up:{user.id}", limit=10, window_seconds=settings.rate_limit_window_seconds
    )
    methods = _strong_methods(db, user)
    if not methods:
        raise AppError(409, "mfa_not_enrolled", "Enroll a second factor first.")
    ticket, raw = mfa_service.issue_ticket(db, settings, user, "step_up")
    return StepUpStartResponse(ticket=raw, methods=methods, expires_at=ticket.expires_at)


@router.post("/step-up/verify-totp", response_model=StrongGrantResponse)
def step_up_verify_totp(
    payload: MfaTicketVerifyRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> StrongGrantResponse:
    limiter.check(
        f"step-up-verify:{user.id}", limit=settings.otp_attempt_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    verified = mfa_service.verify_ticket_totp(db, settings, payload.ticket, "step_up", payload.code)
    if verified.id != user.id:
        raise AppError(401, "invalid_mfa_ticket", "Restart the sign-in flow.")
    grant, raw = mfa_service.issue_strong_grant(db, settings, user, "totp")
    return StrongGrantResponse(grant=raw, method="totp", expires_at=grant.expires_at)


@router.post("/step-up/verify-passkey", response_model=StrongGrantResponse)
def step_up_verify_passkey(
    payload: StepUpPasskeyRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> StrongGrantResponse:
    limiter.check(
        f"step-up-verify:{user.id}", limit=settings.otp_attempt_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    # The passkey assertion is verified first against the session-scoped
    # challenge; only then is the step-up ticket consumed, so a failed
    # assertion leaves the ticket usable for a TOTP fallback.
    owner, _ = webauthn_service.verify_authentication(db, settings, payload.credential)
    if owner.id != user.id:
        raise AppError(401, "invalid_passkey", "The passkey response failed verification.")
    mfa_service.consume_step_up_ticket_for_passkey(db, settings, user, payload.ticket)
    grant, raw = mfa_service.issue_strong_grant(db, settings, user, "passkey")
    return StrongGrantResponse(grant=raw, method="passkey", expires_at=grant.expires_at)


def require_strong_auth(
    request: Request,
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    user: User = Depends(current_user),
) -> User:
    mfa_service.consume_strong_grant(
        db, settings, user, request.headers.get(STRONG_AUTH_HEADER), used_for=request.url.path
    )
    return user


@router.post("/sessions/revoke-others")
def revoke_other_sessions(
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
) -> dict:
    from app.core.security import hash_secret

    current_hash = hash_secret(request.cookies.get(SESSION_COOKIE, ""), settings.secret_key)
    count = mfa_service.revoke_all_sessions(db, user, keep_hash=current_hash)
    return {"revoked": count}


