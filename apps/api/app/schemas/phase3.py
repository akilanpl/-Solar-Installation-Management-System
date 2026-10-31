"""Pydantic models for Phase 3 warehouse, delivery, installation and warranty."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

OperationType = Literal["receipt", "transfer", "delivery", "adjustment"]


def _location(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().upper()
    if not (2 <= len(cleaned) <= 32):
        raise ValueError("Location codes are 2 to 32 characters.")
    return cleaned


class StockOperationLineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_code: str = Field(min_length=2, max_length=32)
    quantity: Decimal
    from_location: str | None = Field(default=None, max_length=32)
    to_location: str | None = Field(default=None, max_length=32)

    @field_validator("component_code")
    @classmethod
    def code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("from_location", "to_location")
    @classmethod
    def locations(cls, value: str | None) -> str | None:
        return _location(value)


class StockOperationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_type: OperationType
    lines: list[StockOperationLineInput] = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=1000)
    source_order_id: uuid.UUID | None = None


class StockOperationLineResponse(BaseModel):
    component_code: str
    quantity: Decimal
    from_location: str | None
    to_location: str | None
    sort_order: int


class StockOperationResponse(BaseModel):
    id: uuid.UUID
    reference: str
    operation_type: str
    status: str
    source_order_id: uuid.UUID | None
    note: str | None
    lines: list[StockOperationLineResponse]
    created_at: datetime
    validated_at: datetime | None


class StockLevelResponse(BaseModel):
    component_code: str
    location_code: str
    on_hand: Decimal


class ReservationResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    component_code: str
    quantity: int
    status: str
    created_at: datetime


class ReservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: uuid.UUID


class SerialScanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    serial_number: str = Field(min_length=4, max_length=64)
    component_code: str = Field(min_length=2, max_length=32)
    operation_id: uuid.UUID | None = None

    @field_validator("serial_number")
    @classmethod
    def serial(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if len(cleaned) < 4:
            raise ValueError("A serial number is required.")
        return cleaned

    @field_validator("component_code")
    @classmethod
    def code(cls, value: str) -> str:
        return value.strip().upper()


class SerialResponse(BaseModel):
    id: uuid.UUID
    serial_number: str
    component_code: str
    status: str
    location_code: str | None
    order_id: uuid.UUID | None
    operation_id: uuid.UUID | None
    created_at: datetime


class SerialAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: uuid.UUID


class ReplenishmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_code: str = Field(min_length=2, max_length=32)
    location_code: str = Field(default="MAIN", max_length=32)
    quantity: int = Field(gt=0, le=100000)

    @field_validator("component_code")
    @classmethod
    def code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("location_code")
    @classmethod
    def location(cls, value: str) -> str:
        cleaned = _location(value)
        assert cleaned is not None
        return cleaned


class ReplenishmentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


class ReplenishmentResponse(BaseModel):
    id: uuid.UUID
    reference: str
    component_code: str
    location_code: str
    quantity: int
    status: str
    requested_by_user_id: uuid.UUID
    decided_by_user_id: uuid.UUID | None
    created_at: datetime


class DeliveryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: uuid.UUID


class DeliveryLineResponse(BaseModel):
    component_code: str
    quantity: int
    sort_order: int


class DeliveryResponse(BaseModel):
    id: uuid.UUID
    reference: str
    order_id: uuid.UUID
    status: str
    lines: list[DeliveryLineResponse]
    confirmed_at: datetime | None
    created_at: datetime


class SchedulingSlotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_starts_at: datetime

    @field_validator("slot_starts_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Slot time must include a timezone.")
        return value


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: uuid.UUID
    technician_user_id: uuid.UUID | None = None
    slot_starts_at: datetime | None = None

    @field_validator("slot_starts_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Slot time must include a timezone.")
        return value


class JobResponse(BaseModel):
    id: uuid.UUID
    reference: str
    order_id: uuid.UUID
    scheduling_request_id: uuid.UUID
    technician_user_id: uuid.UUID | None
    status: str
    slot_starts_at: datetime | None
    arrival_at: datetime | None
    otp_verified: bool
    evidence: dict | None
    signature: dict | None
    completed_at: datetime | None
    customer_code: str | None = None
    created_at: datetime


class JobOtpVerify(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=r"^[0-9]{6}$")


class JobEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    photo_refs: list[str] = Field(min_length=1, max_length=10)
    test_readings: dict = Field(default_factory=dict)
    started_at: datetime
    finished_at: datetime

    @field_validator("started_at", "finished_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Times must include a timezone.")
        return value


class JobSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signature_ref: str = Field(min_length=3, max_length=200)
    customer_confirmed: bool


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: uuid.UUID
    max_results: int = Field(default=5, ge=1, le=20)


class RecommendationResponse(BaseModel):
    technician_user_id: uuid.UUID
    employee_code: str
    open_jobs: int
    reason: str


class WarrantyResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    starts_at: datetime
    ends_at: datetime
    coverage_note: str
