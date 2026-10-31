"""Request and response models for the Phase 2 sales workflow."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Measurement = Decimal


def _two_places(value: Decimal) -> Decimal:
    quantized = value.quantize(Decimal("0.01"))
    if value != quantized:
        raise ValueError("Use at most two decimal places.")
    return quantized


class SurveyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enquiry_id: uuid.UUID


class SurveyAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technician_user_id: uuid.UUID
    appointment_starts_at: datetime | None = None

    @field_validator("appointment_starts_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Appointment time must include a timezone.")
        return value


class SurveySubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    azimuth_deg: Decimal = Field(ge=0, le=360)
    tilt_deg: Decimal = Field(ge=0, le=90)
    shadow_free_area_sqm: Decimal = Field(gt=0, le=100000)
    cable_distance_m: Decimal = Field(ge=0, le=10000)
    grid_connection: Literal["suitable", "unsuitable", "unknown"]
    notes: str = Field(min_length=3, max_length=2000)

    @field_validator(
        "azimuth_deg",
        "tilt_deg",
        "shadow_free_area_sqm",
        "cable_distance_m",
    )
    @classmethod
    def places(cls, value: Decimal) -> Decimal:
        return _two_places(value)

    @field_validator("notes")
    @classmethod
    def notes_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3:
            raise ValueError("Notes must be at least 3 characters.")
        return cleaned


class SurveyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def note_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    content_type: str
    size_bytes: int
    original_filename: str
    created_at: datetime


class SurveyHistoryResponse(BaseModel):
    id: uuid.UUID
    from_status: str | None
    to_status: str
    note: str | None
    created_at: datetime


class SurveyResponse(BaseModel):
    id: uuid.UUID
    reference: str
    enquiry_id: uuid.UUID
    customer_user_id: uuid.UUID
    site_id: uuid.UUID
    assigned_technician_user_id: uuid.UUID | None
    appointment_status: str
    appointment_starts_at: datetime | None
    status: str
    revision_number: int
    revision_of_survey_id: uuid.UUID | None
    azimuth_deg: Decimal | None
    tilt_deg: Decimal | None
    shadow_free_area_sqm: Decimal | None
    cable_distance_m: Decimal | None
    grid_connection: str | None
    notes: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    reviewed_by_user_id: uuid.UUID | None
    evidence: list[EvidenceResponse]
    history: list[SurveyHistoryResponse]
    created_at: datetime
    updated_at: datetime


class SurveyList(BaseModel):
    items: list[SurveyResponse]
    page: int
    page_size: int
    total: int


class TemplateLineResponse(BaseModel):
    component_code: str
    component_name: str
    line_kind: str
    quantity: int
    unit: str
    unit_cost_minor: int
    unit_price_minor: int
    sort_order: int


class TemplateVersionResponse(BaseModel):
    id: uuid.UUID
    package_code: str
    version_number: int
    is_current: bool
    note: str
    lines: list[TemplateLineResponse]


class QuotationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    survey_id: uuid.UUID
    package_code: str = Field(min_length=3, max_length=32)
    discount_minor: int = Field(default=0, ge=0)


class QuotationRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_code: str = Field(min_length=3, max_length=32)
    discount_minor: int = Field(default=0, ge=0)
    revision_request_id: uuid.UUID | None = None


class RevisionRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["capacity", "grid", "components", "pricing", "installation"]
    request_text: str = Field(min_length=3, max_length=2000)

    @field_validator("request_text")
    @classmethod
    def text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3:
            raise ValueError("Describe the requested change.")
        return cleaned


class RevisionRequestResponse(BaseModel):
    id: uuid.UUID
    quotation_id: uuid.UUID
    category: str
    request_text: str
    status: str
    created_at: datetime


class QuotationLineResponse(BaseModel):
    component_code: str | None
    description: str
    line_kind: str
    quantity: int
    unit: str
    unit_cost_minor: int
    unit_price_minor: int
    line_total_minor: int
    sort_order: int


class QuotationResponse(BaseModel):
    id: uuid.UUID
    reference: str
    enquiry_id: uuid.UUID
    survey_id: uuid.UUID
    customer_user_id: uuid.UUID
    site_id: uuid.UUID
    package_code: str
    template_version_id: uuid.UUID
    version_number: int
    supersedes_quotation_id: uuid.UUID | None
    status: str
    material_cost_minor: int
    material_total_minor: int
    installation_total_minor: int
    discount_minor: int
    tax_minor: int
    tax_rate_bps: int
    total_minor: int
    currency_code: str
    expires_at: datetime | None
    issued_at: datetime
    lines: list[QuotationLineResponse]


class QuotationList(BaseModel):
    items: list[QuotationResponse]
    page: int
    page_size: int
    total: int


class PaymentIntentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quotation_id: uuid.UUID
    amount_minor: int = Field(gt=0, le=100_000_000)


class SandboxOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["succeeded", "failed", "unknown"]


class CashReceiptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quotation_id: uuid.UUID
    amount_minor: int = Field(gt=0, le=100_000_000)
    receipt_reference: str = Field(min_length=3, max_length=80)

    @field_validator("receipt_reference")
    @classmethod
    def receipt(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3:
            raise ValueError("A receipt reference is required.")
        return cleaned


class PaymentRequirementResponse(BaseModel):
    quotation_id: uuid.UUID
    currency_code: str
    minimum_advance_minor: int
    full_amount_minor: int
    advance_percent: int
    verified_minor: int
    outstanding_minor: int


class PaymentIntentResponse(BaseModel):
    id: uuid.UUID
    quotation_id: uuid.UUID
    amount_minor: int
    currency_code: str
    method: str
    status: str
    is_test_only: bool
    provider: str
    transaction_reference: str | None
    created_at: datetime


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quotation_id: uuid.UUID


class OrderLineResponse(BaseModel):
    component_code: str | None
    description: str
    line_kind: str
    quantity: int
    unit: str
    unit_price_minor: int
    line_total_minor: int
    sort_order: int


class OrderResponse(BaseModel):
    id: uuid.UUID
    reference: str
    quotation_id: uuid.UUID
    quotation_version: int
    customer_user_id: uuid.UUID
    site_id: uuid.UUID
    package_code: str
    template_version_id: uuid.UUID
    material_total_minor: int
    installation_total_minor: int
    discount_minor: int
    tax_minor: int
    total_minor: int
    currency_code: str
    payment_verification_state: str
    test_only_payment: bool
    status: str
    confirmed_at: datetime
    lines: list[OrderLineResponse]
    warehouse_request_id: uuid.UUID
    scheduling_request_id: uuid.UUID


class OrderList(BaseModel):
    items: list[OrderResponse]
    page: int
    page_size: int
    total: int


class WarehouseLineResponse(BaseModel):
    component_code: str
    description: str
    quantity: int
    unit: str


class WarehouseRequestResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    order_reference: str
    status: str
    lines: list[WarehouseLineResponse]
    created_at: datetime


class SchedulingRequestResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    order_reference: str
    customer_user_id: uuid.UUID
    site_id: uuid.UUID
    work_summary: str
    status: str
    slot_starts_at: datetime | None
    created_at: datetime
