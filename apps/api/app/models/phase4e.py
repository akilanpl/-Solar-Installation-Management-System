"""Phase 4E records: passkeys, MFA, offline sync intake, warranty extensions.

Every table here is new. Phase 4B (and earlier) tables are referenced by
foreign key but never restructured: extensions extend a coverage row's
``ends_at`` while the extension row itself snapshots the original terms, so
historical coverage decisions keep pointing at unchanged snapshots.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

WEBAUTHN_PURPOSES = ("registration", "authentication")
MFA_KINDS = ("totp",)
MFA_TICKET_PURPOSES = ("login", "step_up")
SYNC_OP_TYPES = (
    "survey_draft",
    "repair_diagnostics",
    "repair_work",
    "repair_checklist",
    "measurement",
    "evidence_intent",
)
SYNC_OP_STATUSES = ("received", "applied", "conflict", "rejected")
EXTENSION_STATUSES = (
    "requested",
    "pending_approval",
    "pending_payment",
    "active",
    "rejected",
    "cancelled",
    "expired",
)
EXTENSION_TERMINAL = ("active", "rejected", "cancelled", "expired")
OFFER_STATUSES = ("offered", "superseded", "expired")


class WebauthnChallenge(Base):
    """One-time server challenge for a passkey ceremony.

    The raw challenge is stored base64url-encoded. Challenges are random,
    short-lived (minutes) and consumed on first use, so a database copy is
    not sufficient to complete a ceremony without the authenticator.
    """

    __tablename__ = "webauthn_challenges"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('registration', 'authentication')",
            name="webauthn_challenge_purpose",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    challenge_b64: Mapped[str] = mapped_column(String(128), nullable=False)
    rp_id: Mapped[str] = mapped_column(String(253), nullable=False)
    origin: Mapped[str] = mapped_column(String(253), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WebauthnCredential(Base):
    """One registered passkey: public material only, never private key material."""

    __tablename__ = "webauthn_credentials"
    __table_args__ = (
        UniqueConstraint("credential_id_b64", name="uq_webauthn_credential"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    credential_id_b64: Mapped[str] = mapped_column(String(512), nullable=False)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transports: Mapped[list | None] = mapped_column(JSONB)
    backed_up: Mapped[bool] = mapped_column(nullable=False, default=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="Passkey")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MfaFactor(Base):
    """One enrolled second factor. TOTP secrets are Fernet-encrypted, never plain."""

    __tablename__ = "mfa_factors"
    __table_args__ = (
        CheckConstraint("kind IN ('totp')", name="mfa_factor_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="Authenticator app")
    secret_enc: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MfaRecoveryCode(Base):
    """Single-use recovery codes. Only HMAC hashes are stored."""

    __tablename__ = "mfa_recovery_codes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MfaTicket(Base):
    """Short-lived ticket bridging password verification to second-factor check."""

    __tablename__ = "mfa_tickets"
    __table_args__ = (
        CheckConstraint("purpose IN ('login', 'step_up')", name="mfa_ticket_purpose"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    ticket_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    methods: Mapped[list] = mapped_column(JSONB, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StrongAuthGrant(Base):
    """Fresh step-up proof consumed by sensitive endpoints via X-Strong-Auth."""

    __tablename__ = "strong_auth_grants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    grant_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_for: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TechnicianSyncOperation(Base):
    """Durable record of one queued offline mutation and its server verdict.

    ``(user_id, client_operation_id)`` is unique so a retried upload returns
    the stored verdict instead of applying twice. ``base_field_version`` is
    the client-observed optimistic-lock version; a mismatch yields a conflict
    verdict, never a silent overwrite.
    """

    __tablename__ = "technician_sync_operations"
    __table_args__ = (
        CheckConstraint(
            "op_type IN ('survey_draft', 'repair_diagnostics', 'repair_work', "
            "'repair_checklist', 'measurement', 'evidence_intent')",
            name="sync_op_type",
        ),
        CheckConstraint(
            "status IN ('received', 'applied', 'conflict', 'rejected')",
            name="sync_op_status",
        ),
        UniqueConstraint("user_id", "client_operation_id", name="uq_sync_operation_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    client_operation_id: Mapped[str] = mapped_column(String(80), nullable=False)
    op_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column()
    base_field_version: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WarrantyExtensionTerms(Base):
    """Configurable business policy for warranty extensions, per warranty policy.

    The extension window, duration, price and approval rules are company data
    entered here — never universal constants. Terms are versioned rows; only
    one row per policy is active at a time.
    """

    __tablename__ = "warranty_extension_terms"
    __table_args__ = (
        CheckConstraint("extension_days > 0", name="extension_terms_days"),
        CheckConstraint("price_minor >= 0", name="extension_terms_price"),
        CheckConstraint("window_days >= 0", name="extension_terms_window"),
        CheckConstraint("max_extensions >= 1", name="extension_terms_max"),
        UniqueConstraint("policy_id", "version", name="uq_extension_terms_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranty_policies.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    extension_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    eligible_categories: Mapped[list] = mapped_column(JSONB, nullable=False)
    max_extensions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    requires_approval: Mapped[bool] = mapped_column(nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WarrantyExtensionOffer(Base):
    """The purchase contract for one coverage: exact price, terms and payment need."""

    __tablename__ = "warranty_extension_offers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('offered', 'superseded', 'expired')",
            name="extension_offer_status",
        ),
        UniqueConstraint("coverage_id", "version", name="uq_extension_offer_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    coverage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("serialized_asset_coverage.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    terms_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranty_extension_terms.id"), nullable=False
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranty_policy_versions.id"), nullable=False
    )
    extension_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    payment_required: Mapped[bool] = mapped_column(nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WarrantyExtension(Base):
    """One customer extension request and its lifecycle.

    ``original_ends_at`` snapshots the coverage end before activation so the
    prior manufacturer terms stay visible even after ``ends_at`` is extended.
    Activation never happens from a browser-only event: a paid extension needs
    a recorded, verified payment reference from support/admin.
    """

    __tablename__ = "warranty_extensions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('requested', 'pending_approval', 'pending_payment', 'active', "
            "'rejected', 'cancelled', 'expired')",
            name="warranty_extension_status",
        ),
        UniqueConstraint("idempotency_key", name="uq_warranty_extension_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranty_extension_offers.id"), nullable=False
    )
    offer_version: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_serials.id"), nullable=False
    )
    coverage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("serialized_asset_coverage.id"), nullable=False, index=True
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False, index=True
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranty_policy_versions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    extension_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    original_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_reference: Mapped[str | None] = mapped_column(String(120))
    verified_payment_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_payment_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decision_note: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
