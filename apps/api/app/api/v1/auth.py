from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.cookies import clear_auth_cookies, set_csrf_cookie, set_session_cookie
from app.api.deps import (
    client_ip,
    current_user,
    get_email_sender,
    get_limiter,
    get_settings,
    issue_csrf,
)
from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.core.security import SESSION_COOKIE
from app.db.session import get_db as get_db_dep
from app.models.identity import User
from app.schemas import (
    CsrfResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ResendVerificationRequest,
    SignupRequest,
    SignupResponse,
    VerifyEmailRequest,
)
from app.services import auth_service, mfa_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/csrf", response_model=CsrfResponse)
def read_csrf(response: Response, settings: Settings = Depends(get_settings)) -> CsrfResponse:
    token = issue_csrf()
    set_csrf_cookie(response, settings, token)
    return CsrfResponse(csrf_token=token)


@router.post("/signup", response_model=SignupResponse, status_code=201)
def signup(
    payload: SignupRequest,
    request: Request,
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
    sender=Depends(get_email_sender),
) -> SignupResponse:
    limiter.check(
        f"signup:{client_ip(request)}", limit=8, window_seconds=settings.rate_limit_window_seconds
    )
    user = auth_service.signup(db, settings, sender, payload)
    return SignupResponse(id=user.id, email=user.email, email_verified=False)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> MessageResponse:
    window = settings.rate_limit_window_seconds
    limiter.check(
        f"otp-ip:{client_ip(request)}", limit=settings.otp_attempt_limit, window_seconds=window
    )
    limiter.check(
        f"otp-email:{payload.email}", limit=settings.otp_attempt_limit, window_seconds=window
    )
    auth_service.verify_email(db, settings, payload.email, payload.code)
    return MessageResponse(message="Email verified. You can sign in.")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
    sender=Depends(get_email_sender),
) -> MessageResponse:
    limiter.check(
        f"resend:{client_ip(request)}",
        limit=5,
        window_seconds=settings.rate_limit_window_seconds,
    )
    auth_service.resend_verification(db, settings, sender, payload.email)
    return MessageResponse(message="If the account exists and is unverified, a new code was sent.")


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={202: {"description": "Second factor required; redeem the ticket."}},
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
):
    # The browser may send intended_role. It is not read for authorization.
    _ignored_client_role_hint = payload.intended_role
    del _ignored_client_role_hint
    window = settings.rate_limit_window_seconds
    limiter.check(
        f"login-ip:{client_ip(request)}", limit=settings.login_ip_limit, window_seconds=window
    )
    limiter.check(
        f"login-id:{payload.account_kind}:{payload.identifier.lower()}",
        limit=settings.login_identifier_limit,
        window_seconds=window,
    )
    user, raw = auth_service.authenticate(
        db,
        settings,
        account_kind=payload.account_kind,
        identifier=payload.identifier,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )
    if raw is None:
        # Password was correct but the account has a verified second factor.
        # No session exists yet; the ticket below must be redeemed first.
        limiter.check(
            f"mfa-login:{user.id}", limit=10, window_seconds=settings.rate_limit_window_seconds
        )
        ticket, ticket_raw = mfa_service.issue_ticket(db, settings, user, "login")
        db.flush()
        from fastapi.responses import JSONResponse

        return JSONResponse(  # type: ignore[return-value]
            status_code=202,
            content={
                "mfa_required": True,
                "ticket": ticket_raw,
                "methods": ticket.methods,
                "expires_at": ticket.expires_at.isoformat(),
            },
        )
    set_session_cookie(response, settings, raw)
    set_csrf_cookie(response, settings, issue_csrf())
    return LoginResponse(user=auth_service.to_current_user(user))


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings),
) -> Response:
    auth_service.logout(db, settings, request.cookies.get(SESSION_COOKIE))
    clear_auth_cookies(response, settings)
    response.status_code = 204
    return response


@router.get("/me", response_model=LoginResponse)
def me(user: User = Depends(current_user)) -> LoginResponse:
    return LoginResponse(user=auth_service.to_current_user(user))
