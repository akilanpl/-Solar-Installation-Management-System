"""Phase 4B replacement contracts. Bodies forbid extra fields."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReplacementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: UUID
    old_serial_number: str = Field(min_length=1, max_length=64)
    new_serial_number: str = Field(min_length=1, max_length=64)


class ReplacementResponse(BaseModel):
    id: UUID
    reference: str
    ticket_id: UUID
    old_serial_number: str
    new_serial_number: str
    status: str
    manufacturer_status: str
    issue_operation_id: UUID | None = None
    approved_by_user_id: UUID | None = None
    created_at: datetime


class ManufacturerAuth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=3, max_length=200)


class InspectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: str = Field(pattern="^(quarantined|restocked|scrapped)$")
    note: str = Field(min_length=10, max_length=2000)


class InspectionResponse(BaseModel):
    id: UUID
    replacement_id: UUID
    verdict: str
    note: str
    restock_operation_id: UUID | None = None
    created_at: datetime
