"""Phase 3 location custody and inspected-return records. No external success implied."""

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


class StockAllocation(Base):
    __tablename__ = "stock_allocations"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id", "location_code", name="uq_allocation_reservation_location"
        ),
        CheckConstraint(
            "quantity > 0 AND picked_quantity >= 0 AND picked_quantity <= quantity",
            name="quantities",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stock_reservations.id"), nullable=False, index=True
    )
    location_code: Mapped[str] = mapped_column(
        ForeignKey("warehouse_locations.code"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    picked_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class GoodsReturn(Base):
    __tablename__ = "goods_returns"
    __table_args__ = (
        CheckConstraint("status IN ('authorized','inspected')", name="status"),
        CheckConstraint("quantity > 0", name="quantity"),
        UniqueConstraint("created_by_user_id", "idempotency_key", name="uq_return_idempotency"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    delivery_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("delivery_lines.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    inspection_note: Mapped[str | None] = mapped_column(Text)
    disposition: Mapped[str | None] = mapped_column(String(16))
    operation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stock_operations.id"))
    serial_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("equipment_serials.id"))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    inspected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SupplierOrder(Base):
    __tablename__ = "supplier_orders"
    __table_args__ = (
        CheckConstraint("status IN ('draft','ordered','received','cancelled')", name="status"),
        UniqueConstraint("replenishment_request_id", name="uq_supplier_order_replenishment"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    replenishment_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("replenishment_requests.id"), nullable=False
    )
    supplier_name: Mapped[str] = mapped_column(String(160), nullable=False)
    supplier_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    received_operation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_operations.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
