"""Strict, source-oriented finance commands. No generic arbitrary journal API."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

Money = Annotated[int, Field(strict=True, ge=0, le=9_000_000_000_000)]
PositiveMoney = Annotated[int, Field(strict=True, gt=0, le=9_000_000_000_000)]
Note = Annotated[str, Field(min_length=3, max_length=500)]
Key = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^\S+$")]


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PeriodCreate(Command):
    starts_on: date
    ends_on: date


class PeriodClose(Command):
    evidence: Note


class PolicyCreate(Command):
    key: Key
    label: Note
    approval_reference: Note
    effective_from: date
    effective_to: date
    recognition: Literal["completed_installation_and_approved_service"]
    tax: Literal["preserve_approved_source_snapshot"]
    posting_rules: Literal["invoice_deferred_tax_on_issue_costs_on_approval"]


class Dated(Command):
    posting_date: date
    policy_id: UUID


class FinanceInvoiceCreate(Dated):
    source_kind: Literal["order", "service_invoice"]
    source_id: UUID


class RecognitionCreate(Dated):
    evidence_id: UUID


class PaymentImport(Dated):
    payment_id: UUID
    order_id: UUID
    invoice_id: UUID | None = None


class CreditCreate(Dated):
    source_credit_id: UUID | None = None
    amount_minor: PositiveMoney
    tax_minor: Money
    reason: Note
    evidence_id: UUID
    key: Key


class ReverseCreate(Command):
    posting_date: date
    reason: Note
    evidence_id: UUID


class RateCreate(Command):
    technician_id: UUID
    effective_from: AwareDatetime
    effective_to: AwareDatetime
    hourly_minor: PositiveMoney
    evidence_id: UUID
    key: Key


class TimesheetCreate(Command):
    job_kind: Literal["installation", "repair"]
    job_id: UUID
    check_in: AwareDatetime
    check_out: AwareDatetime
    note: Note
    key: Key


class TimesheetReview(Dated):
    decision: Literal["approved", "rejected"]
    approved_minutes: Annotated[int, Field(strict=True, ge=0, le=1440)]
    note: Note
    evidence_id: UUID


class CostCreate(Dated):
    order_id: UUID
    kind: Literal["material", "expense"]
    ledger_id: UUID | None = None
    amount_minor: PositiveMoney
    evidence_id: UUID
    description: Note
    key: Key


class SettlementCreate(Dated):
    amount_minor: PositiveMoney
    evidence_id: UUID
    bank_reference: Key


class CompletenessCreate(Command):
    order_id: UUID
    evidence_id: UUID
    labour_complete: Literal[True]
    expenses_complete: Literal[True]
    note: Note
    key: Key


class SchemeCreate(Command):
    key: Key
    name: Note
    official_url: Annotated[str, Field(pattern=r"^https://[^\s]+$", max_length=500)]
    version: Note
    effective_from: date
    effective_to: date
    required_documents: Annotated[list[Key], Field(min_length=1, max_length=30)]
    evidence_id: UUID


class SubsidyCreate(Command):
    order_id: UUID
    scheme_id: UUID
    consent_text: Note
    key: Key


class SubsidyDocument(Command):
    document_type: Key
    evidence_id: UUID
    key: Key


class SubsidyTransition(Command):
    action: Literal["reviewed", "submitted", "approved", "rejected", "consent_withdrawn"]
    note: Note
    evidence_id: UUID | None = None
    external_reference: Key | None = None
    key: Key


class RecordResponse(BaseModel):
    id: UUID
    kind: str
    source_key: str
    order_id: UUID | None
    actor_id: UUID
    policy_id: UUID | None
    payload: dict
    request_hash: str
    created_at: AwareDatetime
    model_config = ConfigDict(from_attributes=True)


class PeriodResponse(BaseModel):
    id: UUID
    starts_on: date
    ends_on: date
    status: str
    closure_evidence: str | None
    model_config = ConfigDict(from_attributes=True)


class EvidenceResponse(BaseModel):
    id: UUID
    sha256: str
    content_type: str


class JournalResponse(BaseModel):
    id: UUID
    source_event: str
    record_id: UUID
    period_id: UUID
    posting_date: date
    reversal_of: UUID | None
    lines: list[dict[str, str | int]]


class JobProfit(BaseModel):
    order_id: UUID
    reference: str
    revenue_minor: int
    material_minor: int
    labour_minor: int
    expense_minor: int
    profit_minor: int
    complete: bool
    missing: list[str]
    source_record_ids: list[UUID]


class DashboardResponse(BaseModel):
    currency: Literal["INR"] = "INR"
    recognized_revenue_minor: int
    cash_minor: int
    receivables_minor: int
    payables_minor: int
    advances_minor: int
    deferred_revenue_minor: int
    outstanding_jobs: int
    service_liability_minor: int | None
    service_liability_state: str
    subsidy_status: dict[str, int]
    jobs: list[JobProfit]


class AdvanceAllocation(Dated):
    receipt_id: UUID
    invoice_id: UUID
    amount_minor: PositiveMoney
    key: Key


class LabourAdjustment(Dated):
    delta_minor: Annotated[int, Field(strict=True, ge=-9_000_000_000_000, le=9_000_000_000_000)]
    reason: Note
    evidence_id: UUID
    key: Key
