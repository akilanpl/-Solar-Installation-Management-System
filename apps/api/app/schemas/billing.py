"""Phase 4B billing contracts. Money is integer INR paise. Bodies forbid extras."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PriceBookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=3, max_length=120)
    labour_rates: dict[str, int] = Field(default_factory=dict)
    part_prices: dict[str, int] = Field(default_factory=dict)
    effective_from: datetime


class PriceBookResponse(BaseModel):
    version: int
    label: str
    labour_rates: dict[str, int]
    part_prices: dict[str, int]
    effective_from: datetime
    created_at: datetime


class TaxPolicyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=3, max_length=120)
    rate_bps: int = Field(ge=0)
    effective_from: datetime


class TaxPolicyResponse(BaseModel):
    version: int
    label: str
    rate_bps: int
    effective_from: datetime
    created_at: datetime


class EstimateResponse(BaseModel):
    id: UUID
    reference: str
    ticket_id: UUID
    repair_job_id: UUID
    coverage_decision_id: UUID
    version: int
    lines: list[dict]
    parts_minor: int
    labour_minor: int
    tax_minor: int
    covered_minor: int
    customer_payable_minor: int
    price_book_version: int
    tax_policy_version: int
    status: str
    valid_until: datetime
    created_at: datetime


class EstimateDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(accepted|rejected)$")
    estimate_version: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=2000)


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estimate_id: UUID


class InvoiceResponse(BaseModel):
    id: UUID
    reference: str
    estimate_id: UUID
    estimate_version: int
    ticket_id: UUID
    lines: list[dict]
    parts_minor: int
    labour_minor: int
    tax_minor: int
    covered_minor: int
    customer_payable_minor: int
    credited_minor: int
    consumption_operation_id: UUID | None = None
    status: str
    created_at: datetime


class CreditNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_minor: int = Field(gt=0)
    reason: str = Field(min_length=10, max_length=2000)


class CreditNoteResponse(BaseModel):
    id: UUID
    reference: str
    invoice_id: UUID
    amount_minor: int
    reason: str
    created_at: datetime
