"""Customer sites, enquiries, and the enquiry reference counter."""

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.identity import CustomerProfile, User

CAPACITY_WATTS = (1000, 2000, 3000, 4000, 5000)
ENQUIRY_STATUSES = ("submitted", "under_review", "qualified", "not_qualified")
GRID_PREFERENCES = ("on_grid", "off_grid")

# Sales and admin may move an enquiry only along these edges.
# Repeating the current status is not a transition.
QUALIFICATION_TRANSITIONS: dict[str, set[str]] = {
    "submitted": {"under_review", "qualified", "not_qualified"},
    "under_review": {"qualified", "not_qualified"},
    "qualified": {"under_review"},
    "not_qualified": {"under_review"},
}


class CustomerSite(Base):
    __tablename__ = "customer_sites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False, index=True
    )
    line1: Mapped[str] = mapped_column(String(120), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(6), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="IN")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    customer: Mapped[CustomerProfile] = relationship()


class EnquiryCounter(Base):
    """Per-year counter locked inside the enquiry transaction.

    `nextval` sequences do not roll back. This row does, so a failed insert
    does not consume a customer-visible reference number.
    """

    __tablename__ = "enquiry_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False)


class Enquiry(Base):
    __tablename__ = "enquiries"
    __table_args__ = (
        CheckConstraint(
            "preferred_capacity_w IN (1000, 2000, 3000, 4000, 5000)",
            name="capacity_watts",
        ),
        CheckConstraint("monthly_bill_minor >= 0 AND monthly_bill_minor <= 100000000", name="bill"),
        CheckConstraint("grid_preference IN ('on_grid', 'off_grid')", name="grid"),
        CheckConstraint(
            "status IN ('submitted', 'under_review', 'qualified', 'not_qualified')",
            name="status",
        ),
        CheckConstraint("char_length(currency_code) = 3", name="currency"),
        CheckConstraint(
            "shadow_free_area_sqm IS NULL OR "
            "(shadow_free_area_sqm >= 0 AND shadow_free_area_sqm <= 100000)",
            name="shadow_area",
        ),
        UniqueConstraint("customer_user_id", "idempotency_key", name="uq_enquiries_idempotency"),
        Index("ix_enquiries_customer_created", "customer_user_id", "created_at"),
        Index("ix_enquiries_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customer_sites.id"), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(80), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(10), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(254), nullable=False)
    preferred_capacity_w: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_preference: Mapped[str] = mapped_column(String(16), nullable=False)
    monthly_bill_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    subsidy_interest: Mapped[bool] = mapped_column(Boolean, nullable=False)
    shadow_free_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    grid_connection_suitable: Mapped[bool | None] = mapped_column(Boolean)
    decision_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    qualification_note: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    site: Mapped[CustomerSite] = relationship()
    customer: Mapped[CustomerProfile] = relationship()
    history: Mapped[list["EnquiryStatusHistory"]] = relationship(
        back_populates="enquiry",
        order_by="EnquiryStatusHistory.created_at",
    )


class EnquiryStatusHistory(Base):
    __tablename__ = "enquiry_status_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    enquiry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enquiries.id"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    enquiry: Mapped[Enquiry] = relationship(back_populates="history")
    actor: Mapped[User] = relationship()
