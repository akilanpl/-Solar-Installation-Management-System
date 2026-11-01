"""Phase 4B records: serial-level warranty intelligence and approved repair billing.

Order-level warranties from Phase 3 stay untouched. This module adds the
per-unit layer: versioned policies, per-serial coverage activated from a real
confirmed delivery, immutable coverage decisions with frozen policy snapshots,
manager-approved exceptions, versioned estimates with customer verdicts, and
immutable invoices with pending-only settlement. Phase 4B never posts to a
general ledger; Phase 4C owns company accounting.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COVERAGE_STATES = ("active", "expired", "superseded", "void")
DECISION_VERDICTS = ("covered", "not_covered", "pending_verification", "blocked")
EXCEPTION_DECISIONS = ("covered", "not_covered")
REPLACEMENT_STATUSES = (
    "proposed",
    "approved",
    "pending_manufacturer",
    "issued",
    "installed",
    "cancelled",
)
ESTIMATE_STATUSES = ("proposed", "accepted", "rejected", "superseded", "expired")
INVOICE_STATUSES = ("outstanding", "pending_payment", "credited")
INSPECTION_VERDICTS = ("quarantined", "restocked", "scrapped")


class WarrantyPolicy(Base):
    __tablename__ = "warranty_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    issuer: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WarrantyPolicyVersion(Base):
    """One immutable revision of a policy's rules.

    Durations and component lists are company-configured data, never universal
    constants: the example two-year inverter and twenty-year panel terms from
    the original scenario are entered as versions through the admin API.
    """

    __tablename__ = "warranty_policy_versions"
    __table_args__ = (
        UniqueConstraint("policy_id", "version_number", name="uq_policy_version"),
        CheckConstraint("duration_days > 0", name="policy_version_duration"),
        CheckConstraint("version_number >= 1", name="policy_version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranty_policies.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    applicable_components: Mapped[list] = mapped_column(JSONB, nullable=False)
    covered_fault_categories: Mapped[list] = mapped_column(JSONB, nullable=False)
    covered_components: Mapped[list] = mapped_column(JSONB, nullable=False)
    covered_repair_types: Mapped[list] = mapped_column(JSONB, nullable=False)
    exclusions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    labour_covered: Mapped[bool] = mapped_column(nullable=False, default=False)
    replacement_allowed: Mapped[bool] = mapped_column(nullable=False, default=False)
    replacement_continuation: Mapped[str] = mapped_column(String(16), nullable=False)
    replacement_warranty_days: Mapped[int | None] = mapped_column(Integer)
    manufacturer_auth_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    repeat_replacement_allowed: Mapped[bool] = mapped_column(nullable=False, default=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SerializedAssetCoverage(Base):
    """Coverage of one exact installed unit under one policy version."""

    __tablename__ = "serialized_asset_coverage"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'expired', 'superseded', 'void')",
            name="asset_coverage_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_serials.id"), nullable=False, unique=True
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranty_policy_versions.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales_orders.id"), nullable=False)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False, index=True
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customer_sites.id"))
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deliveries.id"), nullable=False
    )
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    replaced_by_serial_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("equipment_serials.id")
    )
    supersedes_coverage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("serialized_asset_coverage.id")
    )
    void_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CoverageDecision(Base):
    """Immutable verdict for one ticket/serial/policy/fault evaluation.

    Rows are append-only history: the frozen policy and coverage snapshots
    preserve the decision even when the policy is later revised.
    """

    __tablename__ = "coverage_decisions"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('covered', 'not_covered', 'pending_verification', 'blocked')",
            name="coverage_decision_verdict",
        ),
        UniqueConstraint("ticket_id", "idempotency_key", name="uq_coverage_decision_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_serials.id"), nullable=False
    )
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("warranty_policy_versions.id")
    )
    coverage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("serialized_asset_coverage.id")
    )
    policy_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    coverage_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    fault_category: Mapped[str | None] = mapped_column(String(32))
    fault_code: Mapped[str | None] = mapped_column(String(32))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    decided_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WarrantyException(Base):
    """Manager-approved coverage override for one ticket/serial pair."""

    __tablename__ = "warranty_exceptions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('covered', 'not_covered')", name="warranty_exception_decision"
        ),
        UniqueConstraint("ticket_id", "serial_id", name="uq_warranty_exception"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_serials.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(200))
    decided_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ServicePriceBook(Base):
    """One immutable version of approved labour rates and fallback part prices."""

    __tablename__ = "service_price_books"
    __table_args__ = (
        UniqueConstraint("version", name="uq_price_book_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    labour_rates: Mapped[dict] = mapped_column(JSONB, nullable=False)
    part_prices: Mapped[dict] = mapped_column(JSONB, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ServiceTaxPolicy(Base):
    """One immutable version of the approved service tax rate."""

    __tablename__ = "service_tax_policies"
    __table_args__ = (
        UniqueConstraint("version", name="uq_tax_policy_version"),
        CheckConstraint("rate_bps >= 0", name="tax_policy_rate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    rate_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ServiceEstimate(Base):
    """One version of an itemized repair estimate. Accepted rows are immutable."""

    __tablename__ = "service_estimates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'superseded', 'expired')",
            name="service_estimate_status",
        ),
        UniqueConstraint("ticket_id", "version", name="uq_estimate_version"),
        UniqueConstraint("ticket_id", "idempotency_key", name="uq_estimate_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    repair_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_repair_jobs.id"), nullable=False
    )
    coverage_decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coverage_decisions.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    lines: Mapped[list] = mapped_column(JSONB, nullable=False)
    parts_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    labour_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    covered_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_payable_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    price_book_version: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EstimateDecision(Base):
    """Immutable customer verdict on one exact estimate version."""

    __tablename__ = "estimate_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('accepted', 'rejected')", name="estimate_decision_value"
        ),
        UniqueConstraint("estimate_id", name="uq_estimate_decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_estimates.id"), nullable=False
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    estimate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ServiceInvoice(Base):
    """Immutable bill derived from one accepted estimate version.

    Settlement stays outside Phase 4B: without a real provider an invoice
    remains outstanding or payment-pending forever. No route marks paid.
    """

    __tablename__ = "service_invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('outstanding', 'pending_payment', 'credited')",
            name="service_invoice_status",
        ),
        UniqueConstraint("estimate_id", "estimate_version", name="uq_invoice_estimate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_estimates.id"), nullable=False
    )
    estimate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    lines: Mapped[list] = mapped_column(JSONB, nullable=False)
    parts_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    labour_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    covered_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_payable_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    credited_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumption_operation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_operations.id")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ServiceCreditNote(Base):
    """Adjustment against an invoice. The invoice row itself is never edited
    except for the running credited total and status."""

    __tablename__ = "service_credit_notes"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="credit_note_amount"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_invoices.id"), nullable=False, index=True
    )
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReplacementDecision(Base):
    """Authorized swap of a defective installed unit for a warehouse unit."""

    __tablename__ = "replacement_decisions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'approved', 'pending_manufacturer', 'issued', "
            "'installed', 'cancelled')",
            name="replacement_status",
        ),
        CheckConstraint(
            "manufacturer_status IN ('not_required', 'pending', 'approved')",
            name="replacement_manufacturer",
        ),
        UniqueConstraint("ticket_id", "idempotency_key", name="uq_replacement_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    coverage_decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coverage_decisions.id"), nullable=False
    )
    old_serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_serials.id"), nullable=False
    )
    new_serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_serials.id"), nullable=False, unique=True
    )
    issue_operation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_operations.id")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    manufacturer_status: Mapped[str] = mapped_column(String(16), nullable=False)
    manufacturer_evidence_ref: Mapped[str | None] = mapped_column(String(200))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReturnInspection(Base):
    """Inspection verdict for a defective unit returned to the warehouse."""

    __tablename__ = "return_inspections"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('quarantined', 'restocked', 'scrapped')",
            name="return_inspection_verdict",
        ),
        UniqueConstraint("replacement_id", name="uq_return_inspection"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    replacement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("replacement_decisions.id"), nullable=False
    )
    serial_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_serials.id"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    restock_operation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_operations.id")
    )
    inspected_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
