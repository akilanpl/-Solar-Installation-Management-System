"""Phase 3 records: warehouse inventory, reservations, serials, deliveries, jobs, warranty.

Stock truth lives in ``stock_ledger``. Operations move through
``draft`` -> ``ready`` -> ``done``; only validation inserts ledger rows, in
one transaction. Reservations are created with the order flow and consumed
when a delivery operation validates. Delivery confirmation activates the
warranty. Installation jobs require arrival, customer OTP, evidence and
signature before completion.
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

OPERATION_TYPES = ("receipt", "transfer", "delivery", "adjustment")
OPERATION_STATUSES = ("draft", "ready", "done", "cancelled")
RESERVATION_STATUSES = ("reserved", "consumed", "released")
SERIAL_STATUSES = ("in_stock", "reserved", "in_transit", "installed", "faulty")
DELIVERY_STATUSES = ("prepared", "in_transit", "delivered", "confirmed", "cancelled")
REPLENISHMENT_STATUSES = ("proposed", "approved", "rejected", "ordered", "received", "cancelled")
JOB_STATUSES = ("created", "scheduled", "en_route", "on_site", "completed", "cancelled")
WARRANTY_STATUSES = ("active", "expired", "void")


class WarehouseLocation(Base):
    __tablename__ = "warehouse_locations"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class StockOperation(Base):
    __tablename__ = "stock_operations"
    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('receipt', 'transfer', 'delivery', 'adjustment')",
            name="operation_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'ready', 'done', 'cancelled')",
            name="operation_status",
        ),
        UniqueConstraint("created_by_user_id", "idempotency_key", name="uq_stock_operations_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    operation_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    source_order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sales_orders.id"))
    note: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lines: Mapped[list["StockOperationLine"]] = relationship(
        order_by="StockOperationLine.sort_order", cascade="all, delete-orphan"
    )


class StockOperationLine(Base):
    __tablename__ = "stock_operation_lines"
    __table_args__ = (
        CheckConstraint("quantity <> 0", name="quantity_nonzero"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stock_operations.id"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    from_location: Mapped[str | None] = mapped_column(
        ForeignKey("warehouse_locations.code")
    )
    to_location: Mapped[str | None] = mapped_column(ForeignKey("warehouse_locations.code"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stock_operations.id"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), nullable=False, index=True
    )
    location_code: Mapped[str] = mapped_column(
        ForeignKey("warehouse_locations.code"), nullable=False, index=True
    )
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StockReservation(Base):
    __tablename__ = "stock_reservations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserved', 'consumed', 'released')",
            name="reservation_status",
        ),
        CheckConstraint("quantity > 0", name="reservation_quantity"),
        UniqueConstraint("order_id", "component_code", name="uq_reservation_order_component"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EquipmentSerial(Base):
    __tablename__ = "equipment_serials"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_stock', 'reserved', 'in_transit', 'installed', 'faulty')",
            name="serial_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    serial_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    location_code: Mapped[str | None] = mapped_column(ForeignKey("warehouse_locations.code"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sales_orders.id"))
    operation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stock_operations.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('prepared', 'in_transit', 'delivered', 'confirmed', 'cancelled')",
            name="delivery_status",
        ),
        UniqueConstraint("created_by_user_id", "idempotency_key", name="uq_deliveries_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lines: Mapped[list["DeliveryLine"]] = relationship(
        order_by="DeliveryLine.sort_order", cascade="all, delete-orphan"
    )


class DeliveryLine(Base):
    __tablename__ = "delivery_lines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deliveries.id"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class ReplenishmentRequest(Base):
    __tablename__ = "replenishment_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected', 'ordered', 'received', 'cancelled')",
            name="replenishment_status",
        ),
        CheckConstraint("quantity > 0", name="replenishment_quantity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), nullable=False
    )
    location_code: Mapped[str] = mapped_column(
        ForeignKey("warehouse_locations.code"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InstallationJob(Base):
    __tablename__ = "installation_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'scheduled', 'en_route', 'on_site', 'completed', 'cancelled')",
            name="job_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=False, unique=True
    )
    scheduling_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("installation_scheduling_requests.id"), nullable=False
    )
    technician_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    slot_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    signature: Mapped[dict | None] = mapped_column(JSONB)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class InstallationOtp(Base):
    __tablename__ = "installation_otps"
    __table_args__ = (
        CheckConstraint("purpose IN ('job_customer_verify')", name="otp_purpose"),
        Index("ix_installation_otps_job_open", "job_id", postgresql_where=text("consumed_at IS NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("installation_jobs.id"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Warranty(Base):
    __tablename__ = "warranties"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'expired', 'void')",
            name="warranty_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=False, unique=True
    )
    customer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    coverage_note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
