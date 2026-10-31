"""Exact units planned/moved by an auditable stock operation."""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StockSerialMovement(Base):
    __tablename__ = "stock_serial_movements"
    __table_args__ = (UniqueConstraint("operation_id", "serial_id", name="uq_operation_serial"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stock_operations.id"), nullable=False, index=True
    )
    line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stock_operation_lines.id"), nullable=False, index=True
    )
    delivery_line_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("delivery_lines.id"), index=True
    )
    serial_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment_serials.id"), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(64), nullable=False)
