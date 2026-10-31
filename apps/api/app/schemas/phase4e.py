"""Phase 4E request/response models: passkeys, MFA, offline sync, extensions."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PasskeyOptionsResponse(BaseModel):
    options: dict


class PasskeyVerifyRequest(BaseModel):
    credential: dict = Field(min_length=1)
    label: str = Field(default="Passkey", min_length=1, max_length=80)


class PasskeyVerifyLoginRequest(BaseModel):
    credential: dict = Field(min_length=1)


class PasskeyCredentialResponse(BaseModel):
    id: uuid.UUID
    credential_id: str
    label: str
    backed_up: bool
    sign_count: int
    created_at: datetime


class MfaRequiredResponse(BaseModel):
    mfa_required: Literal[True] = True
    ticket: str
    methods: list[str]
    expires_at: datetime


class TotpEnrollStartRequest(BaseModel):
    label: str = Field(default="Authenticator app", min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class TotpEnrollStartResponse(BaseModel):
    factor_id: uuid.UUID
    otpauth_uri: str


class TotpVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class MfaTicketVerifyRequest(BaseModel):
    ticket: str = Field(min_length=16, max_length=128)
    code: str = Field(min_length=4, max_length=32)


class StepUpPasskeyRequest(BaseModel):
    ticket: str = Field(min_length=16, max_length=128)
    credential: dict = Field(min_length=1)


class RevokeRequest(BaseModel):
    password: str | None = Field(default=None, min_length=1, max_length=128)


class MfaStatusResponse(BaseModel):
    totp_enrolled: bool
    passkeys_registered: bool
    recovery_codes_remaining: int


class RecoveryCodesResponse(BaseModel):
    codes: list[str]


class StepUpStartResponse(BaseModel):
    ticket: str
    methods: list[str]
    expires_at: datetime


class StrongGrantResponse(BaseModel):
    grant: str
    method: str
    expires_at: datetime


class SyncOperationRequest(BaseModel):
    op_type: str = Field(min_length=1, max_length=32)
    entity_type: str = Field(default="", max_length=32)
    entity_id: uuid.UUID | None = None
    client_operation_id: str = Field(min_length=8, max_length=80)
    base_field_version: int | None = None
    payload: dict = Field(default_factory=dict)


class SyncBatchRequest(BaseModel):
    operations: list[SyncOperationRequest] = Field(min_length=1, max_length=25)


class SyncVerdictResponse(BaseModel):
    client_operation_id: str
    operation_id: str | None = None
    op_type: str | None = None
    status: str
    result: dict | None = None
    error: dict | None = None
    duplicate: bool = False


class SyncBatchResponse(BaseModel):
    verdicts: list[SyncVerdictResponse]


class SyncOperationRecord(BaseModel):
    client_operation_id: str
    operation_id: str
    op_type: str
    status: str
    result: dict | None = None
    duplicate: bool = False


class OfflineAssignmentResponse(BaseModel):
    retention_days: int
    cached_until: str
    surveys: list[dict]
    repair_jobs: list[dict]


class ExtensionTermsCreate(BaseModel):
    policy_id: uuid.UUID
    extension_days: int = Field(gt=0, le=3650)
    price_minor: int = Field(ge=0, le=100_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    window_days: int = Field(ge=0, le=3650)
    eligible_categories: list[str] = Field(min_length=1, max_length=20)
    max_extensions: int = Field(default=1, ge=1, le=10)
    requires_approval: bool = True


class ExtensionTermsResponse(BaseModel):
    id: uuid.UUID
    policy_id: uuid.UUID
    version: int
    extension_days: int
    price_minor: int
    currency: str
    window_days: int
    eligible_categories: list[str]
    max_extensions: int
    requires_approval: bool
    is_active: bool
    created_at: datetime


class ExtensionOfferResponse(BaseModel):
    id: uuid.UUID
    coverage_id: uuid.UUID
    version: int
    extension_days: int
    price_minor: int
    currency: str
    payment_required: bool
    status: str
    expires_at: datetime


class ExtensionRequestCreate(BaseModel):
    coverage_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=80)


class ExtensionDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ExtensionPaymentRequest(BaseModel):
    payment_reference: str = Field(min_length=4, max_length=120)


class ExtensionResponse(BaseModel):
    id: uuid.UUID
    offer_id: uuid.UUID
    offer_version: int
    serial_id: uuid.UUID
    coverage_id: uuid.UUID
    status: str
    extension_days: int
    price_minor: int
    currency: str
    original_ends_at: datetime
    new_ends_at: datetime | None
    payment_reference: str | None
    decision_note: str | None
    created_at: datetime


class EligibilityResponse(BaseModel):
    eligible: bool
    reason: str | None = None
    serial_number: str | None = None
    coverage_id: str | None = None
    coverage_status: str | None = None
    coverage_ends_at: str | None = None
    policy_code: str | None = None
    policy_version: int | None = None
    extension_days: int | None = None
    price_minor: int | None = None
    currency: str | None = None
    payment_required: bool | None = None
    window_days: int | None = None
    offer_id: str | None = None
    offer_version: int | None = None
