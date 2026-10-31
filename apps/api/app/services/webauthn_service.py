"""Passkey registration and authentication backed by the py-webauthn library.

All cryptographic verification is delegated to ``webauthn``; this module
only manages challenges, replay protection, origin/RP checks (passed into
the library as expectations), credential storage and audit events. Private
key material never reaches the server.
"""

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
    options_to_json_dict,
)
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import expiry_from_now, utcnow
from app.models.identity import User
from app.models.phase4e import WebauthnChallenge, WebauthnCredential
from app.repositories.queries import add_audit

MAX_CREDENTIALS_PER_USER = 10


def _challenge_bytes() -> bytes:
    return secrets.token_bytes(32)


def _store_challenge(
    db: Session, settings: Settings, user_id: uuid.UUID | None, purpose: str
) -> tuple[bytes, WebauthnChallenge]:
    raw = _challenge_bytes()
    row = WebauthnChallenge(
        user_id=user_id,
        purpose=purpose,
        challenge_b64=bytes_to_base64url(raw),
        rp_id=settings.webauthn_rp_id,
        origin=settings.webauthn_origins[0],
        expires_at=expiry_from_now(minutes=settings.webauthn_challenge_ttl_minutes),
    )
    db.add(row)
    db.flush()
    return raw, row


def registration_options(db: Session, settings: Settings, user: User) -> dict:
    active = _active_credentials(db, user.id)
    if len(active) >= MAX_CREDENTIALS_PER_USER:
        raise AppError(409, "passkey_limit", "This account already has the maximum passkeys.")
    raw, _ = _store_challenge(db, settings, user.id, "registration")
    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_name=user.email,
        user_id=user.id.bytes,
        challenge=raw,
        timeout=60000,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(item.credential_id_b64))
            for item in active
        ],
    )
    add_audit(
        db, actor_user_id=user.id, action="passkey.registration_started",
        entity_type="user", entity_id=user.id, metadata={},
    )
    return options_to_json_dict(options)


def _active_credentials(db: Session, user_id: uuid.UUID) -> list[WebauthnCredential]:
    return list(
        db.scalars(
            select(WebauthnCredential)
            .where(
                WebauthnCredential.user_id == user_id,
                WebauthnCredential.revoked_at.is_(None),
            )
            .order_by(WebauthnCredential.created_at)
        ).all()
    )


def _consume_challenge(
    db: Session, user_id: uuid.UUID | None, purpose: str
) -> WebauthnChallenge:
    query = (
        select(WebauthnChallenge)
        .where(
            WebauthnChallenge.purpose == purpose,
            WebauthnChallenge.consumed_at.is_(None),
        )
        .order_by(WebauthnChallenge.created_at.desc())
        .with_for_update()
    )
    if user_id is None:
        query = query.where(WebauthnChallenge.user_id.is_(None))
    else:
        query = query.where(WebauthnChallenge.user_id == user_id)
    row = db.scalar(query)
    if row is None:
        raise AppError(400, "challenge_missing", "Start the passkey ceremony again.")
    if row.expires_at <= utcnow():
        row.consumed_at = utcnow()
        raise AppError(400, "challenge_expired", "The passkey challenge expired. Start again.")
    row.consumed_at = utcnow()
    return row


def verify_registration(
    db: Session, settings: Settings, user: User, credential: dict, label: str
) -> WebauthnCredential:
    row = _consume_challenge(db, user.id, "registration")
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(row.challenge_b64),
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origins,
            require_user_presence=True,
            require_user_verification=True,
        )
    except WebAuthnException:
        add_audit(
            db, actor_user_id=user.id, action="passkey.registration_failed",
            entity_type="user", entity_id=user.id, metadata={},
        )
        raise AppError(400, "invalid_passkey", "The passkey response failed verification.")
    credential_id_b64 = bytes_to_base64url(verified.credential_id)
    duplicate = db.scalar(
        select(WebauthnCredential).where(
            WebauthnCredential.credential_id_b64 == credential_id_b64
        )
    )
    if duplicate is not None:
        raise AppError(409, "credential_in_use", "This passkey is already registered.")
    response_block = credential.get("response") if isinstance(credential, dict) else None
    transports = None
    if isinstance(response_block, dict) and isinstance(response_block.get("transports"), list):
        transports = [str(item) for item in response_block["transports"]]
    stored = WebauthnCredential(
        user_id=user.id,
        credential_id_b64=credential_id_b64,
        public_key=bytes(verified.credential_public_key),
        sign_count=verified.sign_count,
        transports=transports,
        backed_up=bool(verified.credential_backed_up),
        label=label,
    )
    db.add(stored)
    add_audit(
        db, actor_user_id=user.id, action="passkey.registered",
        entity_type="webauthn_credential", entity_id=stored.id,
        metadata={"backed_up": stored.backed_up},
    )
    db.flush()
    return stored


def authentication_options(
    db: Session, settings: Settings, user: User | None
) -> dict:
    if user is None:
        raw, _ = _store_challenge(db, settings, None, "authentication")
        options = generate_authentication_options(
            rp_id=settings.webauthn_rp_id,
            challenge=raw,
            timeout=60000,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        return options_to_json_dict(options)
    active = _active_credentials(db, user.id)
    if not active:
        raise AppError(404, "no_passkeys", "This account has no passkeys.")
    raw, _ = _store_challenge(db, settings, user.id, "authentication")
    options = generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        challenge=raw,
        timeout=60000,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(item.credential_id_b64))
            for item in active
        ],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    return options_to_json_dict(options)


def _credential_from_request(db: Session, credential: dict) -> WebauthnCredential:
    try:
        raw_id = str(credential.get("rawId") or credential.get("id") or "")
        raw_bytes = base64url_to_bytes(raw_id) if raw_id else b""
        candidate_b64 = bytes_to_base64url(raw_bytes)
    except Exception:
        raise AppError(400, "invalid_passkey", "The passkey response failed verification.")
    stored = db.scalar(
        select(WebauthnCredential).where(
            WebauthnCredential.credential_id_b64 == candidate_b64
        )
    )
    if stored is None or stored.revoked_at is not None:
        raise AppError(401, "unknown_credential", "This passkey is not recognized.")
    return stored


def verify_authentication(
    db: Session, settings: Settings, credential: dict
) -> tuple[User, WebauthnCredential]:
    stored = _credential_from_request(db, credential)
    owner = db.get(User, stored.user_id)
    if owner is None or not owner.is_active:
        raise AppError(401, "unknown_credential", "This passkey is not recognized.")
    challenge = _challenge_for_owner(db, owner.id)
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge.challenge_b64),
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origins,
            credential_public_key=bytes(stored.public_key),
            credential_current_sign_count=stored.sign_count,
            require_user_verification=True,
        )
    except WebAuthnException:
        add_audit(
            db, actor_user_id=owner.id, action="passkey.authentication_failed",
            entity_type="webauthn_credential", entity_id=stored.id, metadata={},
        )
        raise AppError(401, "invalid_passkey", "The passkey response failed verification.")
    if not _counter_advances(stored.sign_count, verified.new_sign_count):
        add_audit(
            db, actor_user_id=owner.id, action="passkey.counter_regression",
            entity_type="webauthn_credential", entity_id=stored.id,
            metadata={"stored": stored.sign_count, "presented": verified.new_sign_count},
        )
        raise AppError(401, "counter_regression", "This passkey cannot be used again.")
    stored.sign_count = verified.new_sign_count
    add_audit(
        db, actor_user_id=owner.id, action="passkey.authenticated",
        entity_type="webauthn_credential", entity_id=stored.id, metadata={},
    )
    db.flush()
    return owner, stored


def _challenge_for_owner(db: Session, owner_id: uuid.UUID) -> WebauthnChallenge:
    row = db.scalar(
        select(WebauthnChallenge)
        .where(
            WebauthnChallenge.purpose == "authentication",
            WebauthnChallenge.user_id == owner_id,
            WebauthnChallenge.consumed_at.is_(None),
        )
        .order_by(WebauthnChallenge.created_at.desc())
        .with_for_update()
    )
    if row is not None:
        if row.expires_at <= utcnow():
            row.consumed_at = utcnow()
            raise AppError(400, "challenge_expired", "The passkey challenge expired. Start again.")
        row.consumed_at = utcnow()
        return row
    return _consume_challenge(db, None, "authentication")


def _counter_advances(stored: int, presented: int) -> bool:
    if stored == 0 and presented == 0:
        return True
    return presented > stored


def list_credentials(db: Session, user: User) -> list[WebauthnCredential]:
    return _active_credentials(db, user.id)


def revoke_credential(
    db: Session, user: User, credential_id: uuid.UUID
) -> WebauthnCredential:
    stored = db.get(WebauthnCredential, credential_id)
    if stored is None or stored.user_id != user.id or stored.revoked_at is not None:
        raise AppError(404, "not_found", "Passkey not found.")
    stored.revoked_at = utcnow()
    add_audit(
        db, actor_user_id=user.id, action="passkey.revoked",
        entity_type="webauthn_credential", entity_id=stored.id, metadata={},
    )
    db.flush()
    return stored


