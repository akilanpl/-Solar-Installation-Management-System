"""Account registration, verification, sessions, and staff provisioning."""

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    dummy_password_check,
    expiry_from_now,
    hash_password,
    hash_secret,
    new_otp,
    new_token,
    secrets_match,
    utcnow,
    verify_password,
)
from app.models.identity import (
    CustomerProfile,
    EmailVerificationChallenge,
    EmployeeProfile,
    User,
)
from app.models.identity import (
    Session as DbSession,
)
from app.repositories.queries import (
    active_challenge,
    add_audit,
    get_role,
    get_session_by_hash,
    get_user_by_email,
    get_user_by_employee_code,
)
from app.schemas import CurrentUser, EmployeeCreate, SignupRequest
from app.services.email_sender import OutboundEmail


def _profile_name(user: User) -> tuple[str, str, str | None]:
    if user.customer_profile is not None:
        return user.customer_profile.full_name, user.customer_profile.phone, None
    if user.employee_profile is not None:
        return (
            user.employee_profile.full_name,
            user.employee_profile.phone,
            user.employee_profile.employee_code,
        )
    raise AppError(500, "profile_missing", "This account has no profile.")


def to_current_user(user: User) -> CurrentUser:
    full_name, phone, employee_code = _profile_name(user)
    account_kind = "customer" if user.role_code == "customer" else "employee"
    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role_code,
        account_kind=account_kind,
        email_verified=user.email_verified_at is not None,
        full_name=full_name,
        phone=phone,
        employee_code=employee_code,
    )


def _issue_challenge(db: Session, settings: Settings, user: User) -> str:
    previous = active_challenge(db, user.id)
    if previous is not None:
        previous.consumed_at = utcnow()
    code = new_otp()
    db.add(
        EmailVerificationChallenge(
            user_id=user.id,
            purpose="signup_verify",
            code_hash=hash_secret(code, settings.secret_key),
            expires_at=expiry_from_now(minutes=settings.otp_ttl_minutes),
        )
    )
    return code


def _send_code(sender, email: str, code: str) -> None:
    sender.send(
        OutboundEmail(
            recipient=email,
            subject="SolarOps email verification code",
            body=(
                f"Your SolarOps verification code is {code}. "
                "It expires in 10 minutes and can be used once."
            ),
            code=code,
        )
    )


def signup(db: Session, settings: Settings, sender, payload: SignupRequest) -> User:
    if get_user_by_email(db, payload.email) is not None:
        raise AppError(409, "email_taken", "An account with this email already exists.")
    role = get_role(db, "customer")
    if role is None:
        raise AppError(500, "roles_missing", "Customer role is not configured.")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_code="customer",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(CustomerProfile(user_id=user.id, full_name=payload.full_name, phone=payload.phone))
    code = _issue_challenge(db, settings, user)
    add_audit(
        db,
        actor_user_id=user.id,
        action="user.signed_up",
        entity_type="user",
        entity_id=user.id,
        metadata={"email": user.email},
    )
    db.flush()
    _send_code(sender, user.email, code)
    db.refresh(user)
    return user


def resend_verification(db: Session, settings: Settings, sender, email: str) -> None:
    user = get_user_by_email(db, email)
    # Same response whether or not the email exists, except we still send when it does.
    if user is None or user.role_code != "customer":
        return
    if user.email_verified_at is not None:
        return
    code = _issue_challenge(db, settings, user)
    _send_code(sender, user.email, code)


def verify_email(db: Session, settings: Settings, email: str, code: str) -> None:
    user = get_user_by_email(db, email)
    challenge = active_challenge(db, user.id) if user is not None else None
    if user is None or challenge is None:
        raise AppError(
            400, "invalid_verification_code", "The verification code is invalid or expired."
        )
    if challenge.expires_at <= utcnow() or challenge.consumed_at is not None:
        challenge.consumed_at = challenge.consumed_at or utcnow()
        db.commit()
        raise AppError(
            400, "invalid_verification_code", "The verification code is invalid or expired."
        )
    if not secrets_match(challenge.code_hash, code, settings.secret_key):
        challenge.attempt_count += 1
        if challenge.attempt_count >= settings.otp_max_attempts:
            challenge.consumed_at = utcnow()
        # Persist the failed attempt even though the request itself fails.
        # The outer request dependency would roll this back if we only flushed.
        db.commit()
        raise AppError(
            400, "invalid_verification_code", "The verification code is invalid or expired."
        )
    challenge.consumed_at = utcnow()
    user.email_verified_at = utcnow()
    user.updated_at = utcnow()
    add_audit(
        db,
        actor_user_id=user.id,
        action="user.email_verified",
        entity_type="user",
        entity_id=user.id,
        metadata={},
    )


def authenticate(
    db: Session,
    settings: Settings,
    *,
    account_kind: str,
    identifier: str,
    password: str,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[User, str]:
    """Return the user and a new raw session token.

    `account_kind` chooses email lookup versus employee-id lookup. It does not
    choose the role. The role is read from `users.role_code`.
    """

    if account_kind == "customer":
        user = get_user_by_email(db, identifier.lower())
        if user is not None and user.role_code != "customer":
            user = None
    else:
        user = get_user_by_employee_code(db, identifier.strip().upper())
        if user is not None and user.role_code == "customer":
            user = None
    if user is None:
        dummy_password_check(password)
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    if not verify_password(user.password_hash, password):
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    if not user.is_active:
        raise AppError(403, "account_disabled", "This account is disabled.")
    if user.email_verified_at is None:
        raise AppError(
            403,
            "email_not_verified",
            "Verify the email address before signing in.",
        )
    raw = new_token()
    db.add(
        DbSession(
            user_id=user.id,
            token_hash=hash_secret(raw, settings.secret_key),
            expires_at=expiry_from_now(hours=settings.session_ttl_hours),
            user_agent=(user_agent or "")[:256] or None,
            ip_address=(ip_address or "")[:64] or None,
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="user.login",
        entity_type="user",
        entity_id=user.id,
        metadata={"account_kind": account_kind},
    )
    _load_profile(db, user)
    return user, raw


def _load_profile(db: Session, user: User) -> None:
    if user.role_code == "customer":
        db.refresh(user, attribute_names=["customer_profile"])
    else:
        db.refresh(user, attribute_names=["employee_profile"])


def user_from_session_token(db: Session, settings: Settings, raw_token: str | None) -> User:
    if not raw_token:
        raise AppError(401, "unauthenticated", "Sign in to continue.")
    row = get_session_by_hash(db, hash_secret(raw_token, settings.secret_key))
    if row is None or row.revoked_at is not None or row.expires_at <= utcnow():
        raise AppError(401, "unauthenticated", "Sign in to continue.")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AppError(401, "unauthenticated", "Sign in to continue.")
    _load_profile(db, user)
    return user


def logout(db: Session, settings: Settings, raw_token: str | None) -> None:
    if not raw_token:
        return
    row = get_session_by_hash(db, hash_secret(raw_token, settings.secret_key))
    if row is None or row.revoked_at is not None:
        return
    row.revoked_at = utcnow()
    add_audit(
        db,
        actor_user_id=row.user_id,
        action="user.logout",
        entity_type="session",
        entity_id=row.id,
        metadata={},
    )


def provision_employee(
    db: Session, actor: User, payload: EmployeeCreate
) -> tuple[User, EmployeeProfile]:
    if actor.role_code != "admin":
        raise AppError(403, "forbidden", "Only an administrator can provision employees.")
    role = get_role(db, payload.role)
    if role is None or not role.is_staff:
        raise AppError(400, "invalid_role", "That role cannot be assigned here.")
    if get_user_by_email(db, payload.email) is not None:
        raise AppError(409, "email_taken", "An account with this email already exists.")
    if get_user_by_employee_code(db, payload.employee_code) is not None:
        raise AppError(409, "employee_code_taken", "That employee ID is already in use.")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role_code=payload.role,
        email_verified_at=utcnow(),
        is_active=True,
    )
    db.add(user)
    db.flush()
    profile = EmployeeProfile(
        user_id=user.id,
        employee_code=payload.employee_code,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    db.add(profile)
    add_audit(
        db,
        actor_user_id=actor.id,
        action="employee.provisioned",
        entity_type="user",
        entity_id=user.id,
        metadata={"role": payload.role, "employee_code": payload.employee_code},
    )
    return user, profile


def list_staff(db: Session) -> list[tuple[User, EmployeeProfile]]:
    from app.repositories.queries import list_employees

    return list_employees(db)


def assert_roles(user: User, allowed: set[str]) -> None:
    if user.role_code not in allowed:
        raise AppError(403, "forbidden", "You do not have access to this action.")
