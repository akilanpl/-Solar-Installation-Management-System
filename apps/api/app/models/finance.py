"""Phase 4C append-only finance subledger; amounts are signed-64-bit INR paise."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FinancePeriod(Base):
    __tablename__ = "finance_periods"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="dates"),
        CheckConstraint("status IN ('open','closed')", name="status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="open")
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    closure_evidence: Mapped[str | None] = mapped_column(String(500))


class FinanceRecord(Base):
    __tablename__ = "finance_records"
    __table_args__ = (UniqueConstraint("kind", "source_key", name="uq_finance_record_source"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    source_key: Mapped[str] = mapped_column(String(180))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customer_profiles.user_id"))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    policy_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("finance_records.id"))
    payload: Mapped[dict] = mapped_column(JSONB)
    request_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinanceEntry(Base):
    __tablename__ = "finance_entries"
    __table_args__ = (
        UniqueConstraint("source_event", name="uq_finance_entry_source"),
        UniqueConstraint("reversal_of", name="uq_finance_reversal"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_event: Mapped[str] = mapped_column(String(200))
    record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("finance_records.id"))
    period_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("finance_periods.id"))
    posting_date: Mapped[date] = mapped_column(Date)
    reversal_of: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("finance_entries.id"))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    request_hash: Mapped[str] = mapped_column(String(64))
    transaction_id: Mapped[int] = mapped_column(BigInteger, server_default=text("txid_current()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


ACCOUNTS = (
    "cash",
    "receivable",
    "deferred_revenue",
    "revenue",
    "tax_payable",
    "labour_cost",
    "material_cost",
    "expense",
    "technician_payable",
    "expense_payable",
    "inventory_clearing",
    "customer_advance",
)


class FinanceLine(Base):
    __tablename__ = "finance_lines"
    __table_args__ = (
        CheckConstraint(
            "debit_minor >= 0 AND credit_minor >= 0 AND ((debit_minor > 0 AND credit_minor = 0) OR (credit_minor > 0 AND debit_minor = 0))",
            name="one_side",
        ),
        CheckConstraint(f"account IN {ACCOUNTS}", name="account"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("finance_entries.id"), index=True)
    account: Mapped[str] = mapped_column(String(40))
    debit_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    credit_minor: Mapped[int] = mapped_column(BigInteger, default=0)


class FinanceEvidence(Base):
    __tablename__ = "finance_evidence"
    __table_args__ = (
        CheckConstraint(
            "octet_length(content) > 0 AND octet_length(content) <= 5000000", name="size"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    content_type: Mapped[str] = mapped_column(String(64))
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
