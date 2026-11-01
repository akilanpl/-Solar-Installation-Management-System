"""Phase 2 records: surveys, versioned packages, quotations, payments, orders.

Issued quotation lines are inserted once and never updated. A revision is a
new quotation row. Order confirmation copies those lines into the order and
the warehouse request in the same transaction. Nothing here changes stock.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

SURVEY_STATUSES = (
    "draft",
    "assigned",
    "in_progress",
    "submitted",
    "approved",
    "rejected",
)
QUOTATION_STATUSES = ("issued", "superseded", "withdrawn", "accepted")
PAYMENT_STATUSES = ("pending", "processing", "verified", "failed", "unresolved")


class DocumentCounter(Base):
    __tablename__ = "document_counters"

    series: Mapped[str] = mapped_column(String(16), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False)


class CatalogueComponent(Base):
    __tablename__ = "catalogue_components"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)


class PackageTemplateVersion(Base):
    __tablename__ = "package_template_versions"
    __table_args__ = (
        UniqueConstraint("package_id", "version_number", name="uq_template_version"),
        Index(
            "uq_package_template_current",
            "package_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("solar_packages.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lines: Mapped[list["PackageTemplateLine"]] = relationship(
        order_by="PackageTemplateLine.sort_order",
    )


class PackageTemplateLine(Base):
    __tablename__ = "package_template_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND quantity <= 10000", name="quantity"),
        CheckConstraint("unit_cost_minor >= 0 AND unit_price_minor >= 0", name="money"),
        CheckConstraint("line_kind IN ('material', 'installation')", name="kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("package_template_versions.id"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), nullable=False
    )
    line_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class Survey(Base):
    __tablename__ = "surveys"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'assigned', 'in_progress', 'submitted', 'approved', 'rejected')",
            name="status",
        ),
        CheckConstraint(
            "azimuth_deg IS NULL OR (azimuth_deg >= 0 AND azimuth_deg <= 360)",
            name="azimuth",
        ),
        CheckConstraint("tilt_deg IS NULL OR (tilt_deg >= 0 AND tilt_deg <= 90)", name="tilt"),
        CheckConstraint(
            "shadow_free_area_sqm IS NULL OR "
            "(shadow_free_area_sqm > 0 AND shadow_free_area_sqm <= 100000)",
            name="area",
        ),
        CheckConstraint(
            "cable_distance_m IS NULL OR (cable_distance_m >= 0 AND cable_distance_m <= 10000)",
            name="cable",
        ),
        CheckConstraint(
            "grid_connection IS NULL OR grid_connection IN ('suitable', 'unsuitable', 'unknown')",
            name="grid",
        ),
        CheckConstraint(
            "appointment_status IN ('pending', 'confirmed')",
            name="appointment",
        ),
        UniqueConstraint("enquiry_id", "revision_number", name="uq_survey_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enquiries.id"), nullable=False)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_sites.id"), nullable=False)
    assigned_technician_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    appointment_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    appointment_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_of_survey_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("surveys.id"))
    azimuth_deg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    tilt_deg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    shadow_free_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    cable_distance_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    grid_connection: Mapped[str | None] = mapped_column(String(16))
    notes: Mapped[str | None] = mapped_column(Text)
    field_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    history: Mapped[list["SurveyStatusHistory"]] = relationship(
        order_by="SurveyStatusHistory.created_at",
    )
    evidence: Mapped[list["SurveyEvidence"]] = relationship()


class SurveyStatusHistory(Base):
    __tablename__ = "survey_status_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("surveys.id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SurveyEvidence(Base):
    __tablename__ = "survey_evidence"
    __table_args__ = (CheckConstraint("size_bytes > 0 AND size_bytes <= 5000000", name="size"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("surveys.id"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('issued', 'superseded', 'withdrawn', 'accepted')",
            name="status",
        ),
        CheckConstraint("version_number >= 1", name="version"),
        CheckConstraint(
            "material_total_minor >= 0 AND installation_total_minor >= 0 "
            "AND discount_minor >= 0 AND tax_minor >= 0 AND total_minor >= 0 "
            "AND material_cost_minor >= 0",
            name="money",
        ),
        CheckConstraint(
            "total_minor = material_total_minor + installation_total_minor "
            "- discount_minor + tax_minor",
            name="totals",
        ),
        UniqueConstraint("customer_user_id", "idempotency_key", name="uq_quotations_idempotency"),
        UniqueConstraint("enquiry_id", "version_number", name="uq_quotation_version"),
        Index(
            "uq_quotations_one_active",
            "enquiry_id",
            unique=True,
            postgresql_where=text("status IN ('issued', 'accepted')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enquiries.id"), nullable=False)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surveys.id"), nullable=False)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_sites.id"), nullable=False)
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("solar_packages.id"), nullable=False)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("package_template_versions.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_quotation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("quotations.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    material_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    material_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    installation_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lines: Mapped[list["QuotationLine"]] = relationship(order_by="QuotationLine.sort_order")


class QuotationLine(Base):
    __tablename__ = "quotation_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity"),
        CheckConstraint(
            "unit_cost_minor >= 0 AND unit_price_minor >= 0 AND line_total_minor >= 0",
            name="money",
        ),
        CheckConstraint(
            "line_kind IN ('material', 'installation', 'tax', 'discount')", name="kind"
        ),
        CheckConstraint("line_total_minor = quantity * unit_price_minor", name="extension"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quotations.id"), nullable=False, index=True
    )
    component_code: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    line_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_cost_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class QuotationRevisionRequest(Base):
    __tablename__ = "quotation_revision_requests"
    __table_args__ = (
        CheckConstraint(
            "category IN ('capacity', 'grid', 'components', 'pricing', 'installation')",
            name="category",
        ),
        CheckConstraint("status IN ('open', 'addressed')", name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quotations.id"), nullable=False, index=True
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    request_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class QuotationAcceptance(Base):
    __tablename__ = "quotation_acceptances"

    quotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotations.id"), primary_key=True)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PaymentRequirement(Base):
    __tablename__ = "payment_requirements"
    __table_args__ = (
        CheckConstraint(
            "minimum_advance_minor >= 0 AND minimum_advance_minor <= full_amount_minor",
            name="advance",
        ),
        CheckConstraint("advance_percent >= 1 AND advance_percent <= 100", name="percent"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quotations.id"), nullable=False, unique=True
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    minimum_advance_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    full_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    advance_percent: Mapped[int] = mapped_column(Integer, nullable=False)


class PaymentIntent(Base):
    __tablename__ = "payment_intents"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount"),
        CheckConstraint("method IN ('sandbox', 'cash')", name="method"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'verified', 'failed', 'unresolved')",
            name="status",
        ),
        UniqueConstraint("customer_user_id", "idempotency_key", name="uq_payment_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quotations.id"), nullable=False, index=True
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    is_test_only: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_reference: Mapped[str | None] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    intent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payment_intents.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SalesOrder(Base):
    __tablename__ = "sales_orders"
    __table_args__ = (
        CheckConstraint("status IN ('confirmed')", name="status"),
        CheckConstraint(
            "payment_verification_state IN ('test_verified', 'manually_verified')",
            name="payment_state",
        ),
        CheckConstraint(
            "total_minor = material_total_minor + installation_total_minor "
            "- discount_minor + tax_minor",
            name="totals",
        ),
        UniqueConstraint("quotation_id", name="uq_sales_orders_quotation"),
        UniqueConstraint("enquiry_id", name="uq_sales_orders_enquiry"),
        UniqueConstraint("confirmed_by_user_id", "idempotency_key", name="uq_sales_orders_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    quotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quotations.id"), nullable=False)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_sites.id"), nullable=False)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enquiries.id"), nullable=False)
    survey_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("surveys.id"), nullable=False)
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("package_template_versions.id"), nullable=False
    )
    package_code: Mapped[str] = mapped_column(String(32), nullable=False)
    quotation_version: Mapped[int] = mapped_column(Integer, nullable=False)
    material_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    installation_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    payment_verification_state: Mapped[str] = mapped_column(String(32), nullable=False)
    test_only_payment: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmed_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    lines: Mapped[list["SalesOrderLine"]] = relationship(order_by="SalesOrderLine.sort_order")


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=False, index=True
    )
    component_code: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    line_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class WarehousePreparationRequest(Base):
    __tablename__ = "warehouse_preparation_requests"
    __table_args__ = (CheckConstraint("status IN ('pending_preparation')", name="status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lines: Mapped[list["WarehousePreparationLine"]] = relationship(
        order_by="WarehousePreparationLine.sort_order",
    )


class WarehousePreparationLine(Base):
    __tablename__ = "warehouse_preparation_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouse_preparation_requests.id"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class InstallationSchedulingRequest(Base):
    __tablename__ = "installation_scheduling_requests"
    __table_args__ = (CheckConstraint("status IN ('unscheduled')", name="status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=False, unique=True
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_sites.id"), nullable=False)
    work_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    slot_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
