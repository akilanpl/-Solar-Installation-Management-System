"""Second-factor authentication: TOTP enrollment/verification and recovery codes.

TOTP secrets are Fernet-encrypted with a key derived from the server secret,
so a database copy alone cannot generate codes. Recovery codes are stored as
HMAC hashes and consumed exactly once. Every failure path is audited and both
process-level rate limiting (routes) and per-factor lockouts (here) apply.
"""

import base64
import secrets
import uuid

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import expiry_from_now, hash_secret, new_token, utcnow
from app.models.identity import User
from app.models.phase4e import MfaFactor, MfaRecoveryCode, MfaTicket, StrongAuthGrant
from app.repositories.queries import add_audit

RECOVERY_CODE_GROUPS = 2
RECOVERY_CODE_GROUP_LEN = 4


def _fernet(settings: Settings) -> Fernet:
    digest = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=b"solarops-mfa-v1", info=b"totp-secret"
    ).derive(settings.secret_key.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(digest))


def _verified_totp_factor(db: Session, user_id: uuid.UUID) -> MfaFactor | None:
    return db.scalar(
        select(MfaFactor)
        .where(
            MfaFactor.user_id == user_id,
            MfaFactor.kind == "totp",
            MfaFactor.verified_at.is_not(None),
            MfaFactor.revoked_at.is_(None),
        )
        .order_by(MfaFactor.created_at.desc())
    )


def user_mfa_methods(db: Session, user: User) -> dict:
    from app.models.phase4e import WebauthnCredential

    factor = _verified_totp_factor(db, user.id)
    passkeys = db.scalar(
        select(WebauthnCredential).where(
            WebauthnCredential.user_id == user.id,
            WebauthnCredential.revoked_at.is_(None),
        )
    )
    codes_remaining = len(
        db.scalars(
            select(MfaRecoveryCode).where(
                MfaRecoveryCode.user_id == user.id,
                MfaRecoveryCode.consumed_at.is_(None),
            )
        ).all()
    )
    return {
        "totp_enrolled": factor is not None,
        "totp_factor_id": factor.id if factor is not None else None,
        "passkeys_registered": passkeys is not None,
        "recovery_codes_remaining": codes_remaining,
    }


def needs_mfa_at_login(db: Session, user: User) -> bool:
    return _verified_totp_factor(db, user.id) is not None


def start_totp_enrollment(
    db: Session, settings: Settings, user: User, label: str
) -> tuple[MfaFactor, str]:
    existing = _verified_totp_factor(db, user.id)
    if existing is not None:
        raise AppError(409, "mfa_exists", "An authenticator app is already enrolled.")
    pending = db.scalar(
        select(MfaFactor).where(
            MfaFactor.user_id == user.id,
            MfaFactor.kind == "totp",
            MfaFactor.verified_at.is_(None),
            MfaFactor.revoked_at.is_(None),
        )
    )
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.totp_issuer)
    if pending is None:
        pending = MfaFactor(user_id=user.id, kind="totp", label=label, secret_enc="")
        db.add(pending)
        db.flush()
    pending.secret_enc = _fernet(settings).encrypt(secret.encode("utf-8")).decode("ascii")
    pending.label = label
    pending.attempt_count = 0
    pending.locked_until = None
    add_audit(
        db, actor_user_id=user.id, action="mfa.enrollment_started",
        entity_type="mfa_factor", entity_id=pending.id, metadata={"kind": "totp"},
    )
    db.flush()
    return pending, uri


def _decrypt_secret(settings: Settings, factor: MfaFactor) -> str:
    try:
        return _fernet(settings).decrypt(factor.secret_enc.encode("ascii")).decode("utf-8")
    except InvalidToken:
        raise AppError(500, "mfa_unavailable", "The second factor cannot be read.")


def _is_locked(factor: MfaFactor) -> bool:
    return factor.locked_until is not None and factor.locked_until > utcnow()


def _register_failure(db: Session, settings: Settings, user_id: uuid.UUID, factor: MfaFactor) -> None:
    factor.attempt_count += 1
    if factor.attempt_count >= settings.mfa_max_attempts:
        factor.locked_until = expiry_from_now(minutes=settings.mfa_lockout_minutes)
        factor.attempt_count = 0
    add_audit(
        db, actor_user_id=user_id, action="mfa.verification_failed",
        entity_type="mfa_factor", entity_id=factor.id, metadata={},
    )


def verify_totp_code(settings: Settings, factor: MfaFactor, code: str) -> bool:
    secret = _decrypt_secret(settings, factor)
    return bool(pyotp.TOTP(secret).verify(code.strip(), valid_window=settings.totp_window))


def confirm_totp_enrollment(
    db: Session, settings: Settings, user: User, code: str
) -> uuid.UUID:
    # Wrong codes must count even though the request raises, so the check
    # runs in a dedicated security transaction like email verification does.
    failure: AppError | None = None
    factor_id: uuid.UUID | None = None
    with Session(db.get_bind()) as security_db:
        with security_db.begin():
            factor = security_db.scalar(
                select(MfaFactor)
                .where(
                    MfaFactor.user_id == user.id,
                    MfaFactor.kind == "totp",
                    MfaFactor.verified_at.is_(None),
                    MfaFactor.revoked_at.is_(None),
                )
                .order_by(MfaFactor.created_at.desc())
                .with_for_update()
            )
            if factor is None:
                failure = AppError(
                    404, "no_pending_enrollment", "Start authenticator enrollment first.")
            elif _is_locked(factor):
                failure = AppError(
                    423, "mfa_locked", "Too many wrong codes. Wait and try again.")
            elif not verify_totp_code(settings, factor, code):
                _register_failure(security_db, settings, user.id, factor)
                failure = AppError(
                    401, "invalid_mfa_code", "The authenticator code is incorrect.")
            else:
                factor.verified_at = utcnow()
                factor.attempt_count = 0
                factor.locked_until = None
                add_audit(
                    security_db, actor_user_id=user.id, action="mfa.enrolled",
                    entity_type="mfa_factor", entity_id=factor.id, metadata={"kind": "totp"},
                )
                factor_id = factor.id
    if failure is not None:
        raise failure
    assert factor_id is not None
    return factor_id


def revoke_factor(db: Session, user: User, factor_id: uuid.UUID) -> MfaFactor:
    factor = db.get(MfaFactor, factor_id)
    if factor is None or factor.user_id != user.id or factor.revoked_at is not None:
        raise AppError(404, "not_found", "Second factor not found.")
    factor.revoked_at = utcnow()
    add_audit(
        db, actor_user_id=user.id, action="mfa.revoked",
        entity_type="mfa_factor", entity_id=factor.id, metadata={"kind": factor.kind},
    )
    db.flush()
    return factor


def issue_recovery_codes(db: Session, settings: Settings, user: User) -> list[str]:
    factor = _verified_totp_factor(db, user.id)
    if factor is None:
        raise AppError(409, "mfa_not_enrolled", "Enroll a second factor first.")
    previous = db.scalars(
        select(MfaRecoveryCode).where(MfaRecoveryCode.user_id == user.id)
    ).all()
    for row in previous:
        row.consumed_at = row.consumed_at or utcnow()
    codes = [_new_recovery_code() for _ in range(settings.mfa_recovery_code_count)]
    for code in codes:
        db.add(
            MfaRecoveryCode(
                user_id=user.id, code_hash=hash_secret(code, settings.secret_key)
            )
        )
    add_audit(
        db, actor_user_id=user.id, action="mfa.recovery_codes_issued",
        entity_type="user", entity_id=user.id,
        metadata={"count": len(codes)},
    )
    db.flush()
    return codes


def _new_recovery_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    groups = [
        "".join(secrets.choice(alphabet) for _ in range(RECOVERY_CODE_GROUP_LEN))
        for _ in range(RECOVERY_CODE_GROUPS)
    ]
    return "-".join(groups)


def consume_recovery_code(db: Session, settings: Settings, user: User, code: str) -> bool:
    normalized = code.strip().upper()
    candidates = db.scalars(
        select(MfaRecoveryCode)
        .where(
            MfaRecoveryCode.user_id == user.id,
            MfaRecoveryCode.consumed_at.is_(None),
        )
        .with_for_update()
    ).all()
    for row in candidates:
        if secrets.compare_digest(row.code_hash, hash_secret(normalized, settings.secret_key)):
            row.consumed_at = utcnow()
            add_audit(
                db, actor_user_id=user.id, action="mfa.recovery_used",
                entity_type="mfa_recovery_code", entity_id=row.id, metadata={},
            )
            return True
    add_audit(
        db, actor_user_id=user.id, action="mfa.recovery_failed",
        entity_type="user", entity_id=user.id, metadata={},
    )
    return False


def available_step_up_methods(db: Session, user: User) -> list[str]:
    """Totp, recovery and passkey methods usable for reauthentication."""
    from app.models.phase4e import WebauthnCredential

    methods = available_second_factors(db, user)
    has_passkey = (
        db.scalar(
            select(WebauthnCredential.id).where(
                WebauthnCredential.user_id == user.id,
                WebauthnCredential.revoked_at.is_(None),
            )
        )
        is not None
    )
    if has_passkey:
        methods.append("passkey")
    return methods


def issue_ticket(
    db: Session, settings: Settings, user: User, purpose: str
) -> tuple[MfaTicket, str]:
    if purpose not in {"login", "step_up"}:
        raise AppError(400, "invalid_purpose", "Unknown second-factor purpose.")
    if purpose == "login":
        methods = available_second_factors(db, user)
    else:
        methods = available_step_up_methods(db, user)
    if not methods:
        raise AppError(409, "mfa_not_enrolled", "No second factor is available.")
    raw = new_token()
    ticket = MfaTicket(
        user_id=user.id,
        purpose=purpose,
        ticket_hash=hash_secret(raw, settings.secret_key),
        methods=methods,
        expires_at=expiry_from_now(minutes=settings.mfa_ticket_ttl_minutes),
    )
    db.add(ticket)
    add_audit(
        db, actor_user_id=user.id, action="mfa.challenge_issued",
        entity_type="mfa_ticket", entity_id=ticket.id, metadata={"purpose": purpose},
    )
    db.flush()
    return ticket, raw


def available_second_factors(db: Session, user: User) -> list[str]:
    methods = []
    if _verified_totp_factor(db, user.id) is not None:
        methods.append("totp")
    codes = db.scalars(
        select(MfaRecoveryCode).where(
            MfaRecoveryCode.user_id == user.id,
            MfaRecoveryCode.consumed_at.is_(None),
        )
    ).all()
    if codes:
        methods.append("recovery_code")
    return methods


def _load_ticket(db: Session, settings: Settings, raw_ticket: str, purpose: str) -> MfaTicket:
    ticket = db.scalar(
        select(MfaTicket)
        .where(MfaTicket.ticket_hash == hash_secret(raw_ticket, settings.secret_key))
        .with_for_update()
    )
    if ticket is None or ticket.purpose != purpose or ticket.consumed_at is not None:
        raise AppError(401, "invalid_mfa_ticket", "Restart the sign-in flow.")
    if ticket.expires_at <= utcnow():
        ticket.consumed_at = utcnow()
        raise AppError(401, "mfa_ticket_expired", "The verification window expired.")
    if ticket.attempt_count >= settings.mfa_max_attempts:
        ticket.consumed_at = utcnow()
        raise AppError(429, "rate_limited", "Too many attempts. Wait and try again.")
    return ticket


def consume_step_up_ticket_for_passkey(
    db: Session, settings: Settings, user: User, raw_ticket: str
) -> None:
    ticket = _load_ticket(db, settings, raw_ticket, "step_up")
    if ticket.user_id != user.id:
        raise AppError(401, "invalid_mfa_ticket", "Restart the sign-in flow.")
    ticket.consumed_at = utcnow()
    add_audit(
        db, actor_user_id=user.id, action="mfa.verified",
        entity_type="mfa_ticket", entity_id=ticket.id,
        metadata={"purpose": "step_up", "method": "passkey"},
    )
    db.flush()


def verify_ticket_totp(
    db: Session, settings: Settings, raw_ticket: str, purpose: str, code: str
) -> User:
    # Attempt counts and lockouts must survive the 401 below, so the check
    # runs in a dedicated security transaction like email verification does.
    failure: AppError | None = None
    user_id: uuid.UUID | None = None
    with Session(db.get_bind()) as security_db:
        with security_db.begin():
            try:
                ticket = _load_ticket(security_db, settings, raw_ticket, purpose)
            except AppError as exc:
                failure = exc
                ticket = None
            if failure is None:
                assert ticket is not None
                owner = security_db.get(User, ticket.user_id)
                if owner is None or not owner.is_active:
                    failure = AppError(
                        401, "invalid_mfa_ticket", "Restart the sign-in flow.")
                else:
                    factor = _verified_totp_factor(security_db, owner.id)
                    if factor is None or "totp" not in ticket.methods:
                        failure = AppError(
                            409, "mfa_not_enrolled", "No second factor is available.")
                    elif _is_locked(factor):
                        failure = AppError(
                            423, "mfa_locked", "Too many wrong codes. Wait and try again.")
                    elif not verify_totp_code(settings, factor, code):
                        ticket.attempt_count += 1
                        _register_failure(security_db, settings, owner.id, factor)
                        failure = AppError(
                            401, "invalid_mfa_code",
                            "The authenticator code is incorrect.")
                    else:
                        ticket.consumed_at = utcnow()
                        factor.attempt_count = 0
                        add_audit(
                            security_db, actor_user_id=owner.id, action="mfa.verified",
                            entity_type="mfa_ticket", entity_id=ticket.id,
                            metadata={"purpose": purpose, "method": "totp"},
                        )
                        user_id = owner.id
    if failure is not None:
        raise failure
    assert user_id is not None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(401, "invalid_mfa_ticket", "Restart the sign-in flow.")
    return user


def verify_ticket_recovery(
    db: Session, settings: Settings, raw_ticket: str, purpose: str, code: str
) -> User:
    failure: AppError | None = None
    user_id: uuid.UUID | None = None
    with Session(db.get_bind()) as security_db:
        with security_db.begin():
            try:
                ticket = _load_ticket(security_db, settings, raw_ticket, purpose)
            except AppError as exc:
                failure = exc
                ticket = None
            if failure is None:
                assert ticket is not None
                owner = security_db.get(User, ticket.user_id)
                if owner is None or not owner.is_active:
                    failure = AppError(
                        401, "invalid_mfa_ticket", "Restart the sign-in flow.")
                elif "recovery_code" not in ticket.methods:
                    failure = AppError(
                        409, "mfa_not_enrolled", "No recovery codes are available.")
                elif not consume_recovery_code(security_db, settings, owner, code):
                    ticket.attempt_count += 1
                    failure = AppError(
                        401, "invalid_mfa_code", "The recovery code is incorrect.")
                else:
                    ticket.consumed_at = utcnow()
                    add_audit(
                        security_db, actor_user_id=owner.id, action="mfa.verified",
                        entity_type="mfa_ticket", entity_id=ticket.id,
                        metadata={"purpose": purpose, "method": "recovery_code"},
                    )
                    user_id = owner.id
    if failure is not None:
        raise failure
    assert user_id is not None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(401, "invalid_mfa_ticket", "Restart the sign-in flow.")
    return user


def issue_strong_grant(
    db: Session, settings: Settings, user: User, method: str
) -> tuple[StrongAuthGrant, str]:
    raw = new_token()
    grant = StrongAuthGrant(
        user_id=user.id,
        grant_hash=hash_secret(raw, settings.secret_key),
        method=method,
        expires_at=expiry_from_now(minutes=settings.strong_auth_ttl_minutes),
    )
    db.add(grant)
    add_audit(
        db, actor_user_id=user.id, action="strong_auth.granted",
        entity_type="strong_auth_grant", entity_id=grant.id, metadata={"method": method},
    )
    db.flush()
    return grant, raw


def consume_strong_grant(
    db: Session, settings: Settings, user: User, raw_grant: str | None, used_for: str
) -> None:
    if not raw_grant:
        raise AppError(403, "strong_auth_required", "Reauthenticate to continue.")
    grant = db.scalar(
        select(StrongAuthGrant)
        .where(StrongAuthGrant.grant_hash == hash_secret(raw_grant, settings.secret_key))
        .with_for_update()
    )
    if (
        grant is None
        or grant.user_id != user.id
        or grant.expires_at <= utcnow()
    ):
        add_audit(
            db, actor_user_id=user.id, action="strong_auth.rejected",
            entity_type="user", entity_id=user.id, metadata={"used_for": used_for},
        )
        raise AppError(403, "strong_auth_required", "Reauthenticate to continue.")
    grant.used_at = utcnow()
    grant.used_for = used_for


def revoke_all_sessions(db: Session, user: User, keep_hash: str | None = None) -> int:
    from app.models.identity import Session as DbSession

    rows = db.scalars(
        select(DbSession).where(
            DbSession.user_id == user.id, DbSession.revoked_at.is_(None)
        )
    ).all()
    count = 0
    for row in rows:
        if keep_hash is not None and secrets.compare_digest(row.token_hash, keep_hash):
            continue
        row.revoked_at = utcnow()
        count += 1
    if count:
        add_audit(
            db, actor_user_id=user.id, action="user.sessions_revoked",
            entity_type="user", entity_id=user.id, metadata={"count": count},
        )
    return count
