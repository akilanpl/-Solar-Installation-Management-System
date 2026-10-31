"""Minimal provider facts; never store card secrets or entire webhook payloads."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProviderPaymentOrder(Base):
    __tablename__ = "provider_payment_orders"
    __table_args__ = (
        CheckConstraint("refunded_minor >= 0 AND unapplied_minor >= 0", name="amounts"),
    )
    intent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payment_intents.id"), primary_key=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    refunded_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unapplied_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderEvent(Base):
    __tablename__ = "provider_events"
    event_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    body_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    intent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payment_intents.id"))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
