"""Phase 4B warranty contracts. Bodies forbid extra fields."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PolicyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=3, max_length=32)
    issuer: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=64)
    description: str = Field(min_length=10, max_length=2000)


class PolicyResponse(BaseModel):
    id: UUID
    code: str
    issuer: str
    category: str
    description: str
    created_at: datetime


class PolicyVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_days: int = Field(gt=0)
    applicable_components: list[str] = Field(default_factory=list)
    covered_fault_categories: list[str] = Field(min_length=1)
    covered_components: list[str] = Field(default_factory=list)
    covered_repair_types: list[str] = Field(default_factory=list)
    exclusions: dict = Field(default_factory=lambda: {"fault_categories": [], "components": []})
    labour_covered: bool = False
    replacement_allowed: bool = False
    replacement_continuation: str = Field(default="remainder", pattern="^(remainder|fixed_days)$")
    replacement_warranty_days: int | None = Field(default=None, gt=0)
    manufacturer_auth_required: bool = False
    repeat_replacement_allowed: bool = False
    effective_from: datetime
    effective_to: datetime | None = None


class PolicyVersionResponse(BaseModel):
    id: UUID
    policy_id: UUID
    version_number: int
    duration_days: int
    applicable_components: list[str]
    covered_fault_categories: list[str]
    covered_components: list[str]
    covered_repair_types: list[str]
    exclusions: dict
    labour_covered: bool
    replacement_allowed: bool
    replacement_continuation: str
    replacement_warranty_days: int | None
    manufacturer_auth_required: bool
    repeat_replacement_allowed: bool
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime


class CoverageResponse(BaseModel):
    coverage_id: UUID
    serial_number: str | None = None
    component_code: str | None = None
    policy_code: str | None = None
    policy_version: int | None = None
    status: str
    starts_at: datetime
    ends_at: datetime
    order_id: UUID


class DecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: UUID
    serial_number: str = Field(min_length=1, max_length=64)
    fault_category: str | None = Field(default=None, max_length=32)
    evaluated_at: datetime | None = None


class DecisionResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    serial_number: str
    policy_version: int | None = None
    fault_category: str | None = None
    evaluated_at: datetime
    verdict: str
    reason: str
    coverage_status: str | None = None
    created_at: datetime


class ExceptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: UUID
    serial_number: str = Field(min_length=1, max_length=64)
    decision: str = Field(pattern="^(covered|not_covered)$")
    reason: str = Field(min_length=10, max_length=2000)
    evidence_ref: str | None = Field(default=None, max_length=200)


class ExceptionResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    decision: str
    reason: str
    evidence_ref: str | None = None
    created_at: datetime


class VoidCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=10, max_length=2000)
