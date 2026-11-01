"""Pydantic request and response models for implemented endpoints.

Field limits here are the first validation gate. PostgreSQL constraints are
the last. The browser repeats the same rules so users see errors early, but
a client that skips them still cannot persist invalid rows.
"""

import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enquiry import CAPACITY_WATTS
from app.schemas.phase4e import (  # noqa: F401
    EligibilityResponse,
    ExtensionDecisionRequest,
    ExtensionOfferResponse,
    ExtensionPaymentRequest,
    ExtensionRequestCreate,
    ExtensionResponse,
    ExtensionTermsCreate,
    ExtensionTermsResponse,
    MfaRequiredResponse,
    MfaStatusResponse,
    MfaTicketVerifyRequest,
    OfflineAssignmentResponse,
    PasskeyCredentialResponse,
    PasskeyOptionsResponse,
    PasskeyVerifyLoginRequest,
    PasskeyVerifyRequest,
    RecoveryCodesResponse,
    RevokeRequest,
    StepUpPasskeyRequest,
    StepUpStartResponse,
    StrongGrantResponse,
    SyncBatchRequest,
    SyncBatchResponse,
    SyncOperationRecord,
    SyncOperationRequest,
    SyncVerdictResponse,
    TotpEnrollStartRequest,
    TotpEnrollStartResponse,
    TotpVerifyRequest,
)

PHONE = re.compile(r"^[6-9][0-9]{9}$")
PIN = re.compile(r"^[1-9][0-9]{5}$")
EMPLOYEE_CODE = re.compile(r"^EMP-[A-Z0-9-]{2,24}$")
IDEMPOTENCY = re.compile(r"^[A-Za-z0-9_-]{8,80}$")

EnquiryStatus = Literal["submitted", "under_review", "qualified", "not_qualified"]
GridPreference = Literal["on_grid", "off_grid"]
StaffRole = Literal[
    "technician",
    "sales",
    "warehouse_staff",
    "warehouse_manager",
    "support",
    "admin",
]


def _clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > 80:
        raise ValueError("Enter a name between 1 and 80 characters.")
    return cleaned


def _password(value: str) -> str:
    if len(value) < 10 or len(value) > 128:
        raise ValueError("Password must be 10 to 128 characters.")
    if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
        raise ValueError("Password must include a letter and a digit.")
    return value


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


class ErrorResponse(BaseModel):
    error: ErrorBody


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str
    email: EmailStr
    phone: str
    password: str

    @field_validator("full_name")
    @classmethod
    def name(cls, value: str) -> str:
        return _clean_name(value)

    @field_validator("email")
    @classmethod
    def email_lower(cls, value: EmailStr) -> str:
        return value.lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE.fullmatch(value):
            raise ValueError("Enter a 10-digit Indian mobile number.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _password(value)


class SignupResponse(BaseModel):
    id: uuid.UUID
    email: str
    email_verified: bool


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    code: str = Field(pattern=r"^[0-9]{6}$")

    @field_validator("email")
    @classmethod
    def email_lower(cls, value: EmailStr) -> str:
        return value.lower()


class ResendVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr

    @field_validator("email")
    @classmethod
    def email_lower(cls, value: EmailStr) -> str:
        return value.lower()


class MessageResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    """`intended_role` is accepted and discarded.

    The login screen may ask which portal the person expects to open. That
    value is not an authorization input.
    """

    model_config = ConfigDict(extra="forbid")

    account_kind: Literal["customer", "employee"]
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    intended_role: str | None = None


class CurrentUser(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    account_kind: Literal["customer", "employee"]
    email_verified: bool
    full_name: str
    phone: str
    employee_code: str | None


class LoginResponse(BaseModel):
    user: CurrentUser


class CsrfResponse(BaseModel):
    csrf_token: str


class SiteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line1: str = Field(min_length=3, max_length=120)
    line2: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=80)
    postal_code: str

    @field_validator("line1", "city", "state")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("This field is too short.")
        return cleaned

    @field_validator("line2")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("postal_code")
    @classmethod
    def pin(cls, value: str) -> str:
        if not PIN.fullmatch(value):
            raise ValueError("Enter a 6-digit PIN code.")
        return value


class EnquiryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_name: str
    contact_phone: str
    contact_email: EmailStr
    site: SiteInput
    preferred_capacity_w: int
    grid_preference: GridPreference
    monthly_bill_minor: int = Field(ge=0, le=100_000_000)
    subsidy_interest: bool

    @field_validator("contact_name")
    @classmethod
    def name(cls, value: str) -> str:
        return _clean_name(value)

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, value: str) -> str:
        if not PHONE.fullmatch(value):
            raise ValueError("Enter a 10-digit Indian mobile number.")
        return value

    @field_validator("contact_email")
    @classmethod
    def email_lower(cls, value: EmailStr) -> str:
        return value.lower()

    @field_validator("preferred_capacity_w")
    @classmethod
    def capacity(cls, value: int) -> int:
        if value not in CAPACITY_WATTS:
            raise ValueError("Capacity must be 1, 2, 3, 4, or 5 kW (1000–5000 W).")
        return value


class SiteResponse(BaseModel):
    id: uuid.UUID
    line1: str
    line2: str | None
    city: str
    state: str
    postal_code: str
    country_code: str


class HistoryResponse(BaseModel):
    id: uuid.UUID
    from_status: str | None
    to_status: str
    actor_role: str
    note: str | None
    created_at: datetime


class EnquirySummary(BaseModel):
    id: uuid.UUID
    reference: str
    status: EnquiryStatus
    contact_name: str
    preferred_capacity_w: int
    grid_preference: GridPreference
    monthly_bill_minor: int
    currency_code: str
    subsidy_interest: bool
    shadow_free_area_sqm: Decimal | None
    grid_connection_suitable: bool | None
    decision_by_user_id: uuid.UUID | None
    decision_at: datetime | None
    qualification_note: str | None
    created_at: datetime
    updated_at: datetime


class EnquiryDetail(EnquirySummary):
    contact_phone: str
    contact_email: str
    site: SiteResponse
    history: list[HistoryResponse]


class EnquiryList(BaseModel):
    items: list[EnquirySummary]
    page: int
    page_size: int
    total: int


class QualificationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["under_review", "qualified", "not_qualified"]
    note: str | None = Field(default=None, max_length=500)
    shadow_free_area_sqm: Decimal | None = Field(default=None, ge=0, le=100000)
    grid_connection_suitable: bool | None = None
    acknowledge_downstream: bool = False

    @field_validator("note")
    @classmethod
    def note_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class PackageResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    category: str
    grid_type: str | None
    capacity_w: int | None
    description: str
    is_active: bool


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    full_name: str
    phone: str
    employee_code: str
    role: StaffRole
    password: str

    @field_validator("email")
    @classmethod
    def email_lower(cls, value: EmailStr) -> str:
        return value.lower()

    @field_validator("full_name")
    @classmethod
    def name(cls, value: str) -> str:
        return _clean_name(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE.fullmatch(value):
            raise ValueError("Enter a 10-digit Indian mobile number.")
        return value

    @field_validator("employee_code")
    @classmethod
    def code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not EMPLOYEE_CODE.fullmatch(normalized):
            raise ValueError("Employee ID must look like EMP-SALES-001.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _password(value)


class EmployeeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str
    employee_code: str
    role: str
    is_active: bool
    email_verified: bool


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadyResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["up"]


class DevMailboxMessage(BaseModel):
    recipient: str
    subject: str
    body: str
    code: str
    created_at: str


def parse_idempotency_key(value: str | None) -> str:
    if value is None or not IDEMPOTENCY.fullmatch(value):
        raise ValueError("Send an Idempotency-Key header of 8 to 80 letters, digits, '_' or '-'.")
    return value
