"""Versioned product terms and serial-level coverage, separate from legacy estimates."""

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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductWarrantyPolicy(Base):
    __tablename__ = "product_warranty_policies"
    __table_args__ = (
        UniqueConstraint("component_code", "version", name="uq_product_warranty_version"),
        CheckConstraint("months > 0 AND months <= 600", name="duration"),
        CheckConstraint("activation_event IN ('delivery','installation')", name="activation"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    months: Mapped[int] = mapped_column(Integer, nullable=False)
    activation_event: Mapped[str] = mapped_column(String(16), nullable=False)
    terms: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OrderWarrantyTerm(Base):
    __tablename__ = "order_warranty_terms"
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales_orders.id"), primary_key=True)
    component_code: Mapped[str] = mapped_column(
        ForeignKey("catalogue_components.code"), primary_key=True
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_warranty_policies.id"), nullable=False
    )


class SerialWarranty(Base):
    __tablename__ = "serial_warranties"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    serial_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_serials.id"), nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales_orders.id"), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_warranty_policies.id"), nullable=False
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deliveries.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    void_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("serial_id", "order_id", name="uq_serial_order_warranty"),
        CheckConstraint("status IN ('active','void')", name="status"),
    )
