"""Phase 4A records: customer complaints through to confirmed resolution.

A complaint references the owning customer's confirmed order and, when the
customer names a unit, one installed equipment serial from that order. The
ticket state machine is enforced in ``ticket_service``; the database backs it
with status check constraints and row locks. Warranty billing and replacement
rules belong to Phase 4B: this module records which parts were used but never
prices them or moves stock.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

TICKET_STATUSES = (
    "open",
    "triaged",
    "assigned",
    "in_progress",
    "waiting_customer",
    "resolved",
    "customer_confirmed",
    "closed",
    "cancelled",
)

TICKET_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "open": ("triaged", "cancelled"),
    "triaged": ("assigned", "waiting_customer", "cancelled"),
    "assigned": ("in_progress", "waiting_customer", "cancelled"),
    "in_progress": ("waiting_customer", "resolved"),
    "waiting_customer": ("triaged", "assigned", "in_progress"),
    "resolved": ("customer_confirmed", "in_progress"),
    "customer_confirmed": ("closed", "in_progress"),
    "closed": ("in_progress",),
    "cancelled": (),
}

REPAIR_JOB_STATUSES = ("assigned", "in_progress", "work_submitted", "cancelled")

CUSTOMER_URGENCIES = ("low", "normal", "high", "urgent")
CONTACT_PREFERENCES = ("email", "phone", "either")
VERIFIED_PRIORITIES = ("low", "normal", "high", "critical")
TICKET_CATEGORIES = ("inverter", "panel", "battery", "mounting", "wiring", "monitoring", "other")


class ServiceTicket(Base):
    __tablename__ = "service_tickets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'triaged', 'assigned', 'in_progress', "
            "'waiting_customer', 'resolved', 'customer_confirmed', 'closed', 'cancelled')",
            name="service_ticket_status",
        ),
        CheckConstraint(
            "customer_urgency IN ('low', 'normal', 'high', 'urgent')",
            name="service_ticket_urgency",
        ),
        CheckConstraint(
            "contact_preference IN ('email', 'phone', 'either')",
            name="service_ticket_contact",
        ),
        CheckConstraint(
            "verified_priority IS NULL OR verified_priority IN ('low', 'normal', 'high', 'critical')",
            name="service_ticket_verified_priority",
        ),
        CheckConstraint(
            "category IS NULL OR category IN "
            "('inverter', 'panel', 'battery', 'mounting', 'wiring', 'monitoring', 'other')",
            name="service_ticket_category",
        ),
        CheckConstraint("resolution_version >= 0", name="service_ticket_resolution_version"),
        UniqueConstraint(
            "customer_user_id", "idempotency_key", name="uq_service_tickets_idempotency"
        ),
        Index("ix_service_tickets_customer_status", "customer_user_id", "status"),
        Index("ix_service_tickets_order", "order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customer_sites.id"))
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales_orders.id"), nullable=False)
    serial_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("equipment_serials.id"))
    fault_code: Mapped[str | None] = mapped_column(String(32))
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    customer_urgency: Mapped[str] = mapped_column(String(16), nullable=False)
    contact_preference: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str | None] = mapped_column(String(16))
    verified_priority: Mapped[str | None] = mapped_column(String(16))
    assigned_support_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    escalated: Mapped[bool] = mapped_column(nullable=False, default=False)
    resolution_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolution_summary: Mapped[dict | None] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    events: Mapped[list["ServiceTicketEvent"]] = relationship(
        order_by="ServiceTicketEvent.created_at",
    )


class ServiceTicketEvent(Base):
    __tablename__ = "service_ticket_events"
    __table_args__ = (
        Index("ix_service_ticket_events_ticket", "ticket_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ServiceTicketAttachment(Base):
    __tablename__ = "service_ticket_attachments"
    __table_args__ = (
        CheckConstraint("size_bytes > 0 AND size_bytes <= 5000000", name="ticket_attachment_size"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    repair_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ticket_repair_jobs.id")
    )
    storage_key: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TicketRepairJob(Base):
    __tablename__ = "ticket_repair_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('assigned', 'in_progress', 'work_submitted', 'cancelled')",
            name="repair_job_status",
        ),
        UniqueConstraint(
            "ticket_id", "idempotency_key", name="uq_repair_jobs_idempotency"
        ),
        Index("ix_repair_jobs_technician_status", "technician_user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales_orders.id"), nullable=False)
    serial_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("equipment_serials.id"))
    technician_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scheduled_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    work_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    work_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    diagnostics: Mapped[dict | None] = mapped_column(JSONB)
    work_performed: Mapped[str | None] = mapped_column(Text)
    parts_used: Mapped[list | None] = mapped_column(JSONB)
    summary: Mapped[str | None] = mapped_column(Text)
    summary_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    field_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ResolutionAcknowledgment(Base):
    """Immutable customer verdict on one exact resolution version.

    Rows are insert-only: no route updates or deletes them, and
    ``(ticket_id, summary_version)`` is unique so a version can be accepted or
    disputed exactly once. A dispute forces a new resolution version.
    """

    __tablename__ = "resolution_acknowledgments"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('confirmed', 'disputed')", name="acknowledgment_decision"
        ),
        UniqueConstraint(
            "ticket_id", "summary_version", name="uq_acknowledgment_version"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_tickets.id"), nullable=False, index=True
    )
    repair_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_repair_jobs.id"), nullable=False
    )
    summary_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
