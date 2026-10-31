"""Phase 4A request and response contracts.

The customer never sets ownership, status, references, or priority: those come
from the session and from support triage. Bodies forbid extra fields so a
client cannot smuggle them in.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    site_id: UUID | None = None
    serial_number: str | None = Field(default=None, max_length=64)
    fault_code: str | None = Field(default=None, max_length=32)
    symptoms: str = Field(min_length=10, max_length=2000)
    customer_urgency: str = Field(pattern="^(low|normal|high|urgent)$")
    contact_preference: str = Field(pattern="^(email|phone|either)$")


class TicketSummary(BaseModel):
    id: UUID
    reference: str
    status: str
    category: str | None
    verified_priority: str | None
    customer_urgency: str
    assigned_support_user_id: UUID | None
    order_id: UUID
    created_at: datetime
    updated_at: datetime


class TicketList(BaseModel):
    items: list[TicketSummary]
    total: int
    page: int
    page_size: int


class WarrantyInfo(BaseModel):
    status: str
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    coverage_note: str | None = None


class TicketEventResponse(BaseModel):
    id: UUID
    from_status: str | None
    to_status: str | None
    actor_user_id: UUID
    action: str
    reason: str | None
    created_at: datetime


class AttachmentResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by_user_id: UUID
    created_at: datetime


class RepairJobResponse(BaseModel):
    id: UUID
    reference: str
    ticket_id: UUID
    technician_user_id: UUID
    status: str
    scheduled_starts_at: datetime | None
    arrival_at: datetime | None
    work_started_at: datetime | None
    work_finished_at: datetime | None
    diagnostics: dict | None = None
    work_performed: str | None = None
    parts_used: list | None = None
    summary: str | None = None
    summary_version: int
    created_at: datetime
    updated_at: datetime


class AcknowledgmentResponse(BaseModel):
    id: UUID
    summary_version: int
    payload_hash: str
    decision: str
    customer_user_id: UUID
    created_at: datetime


class TicketDetail(BaseModel):
    id: UUID
    reference: str
    status: str
    customer_user_id: UUID
    site_id: UUID | None
    order_id: UUID
    serial_number: str | None = None
    fault_code: str | None
    symptoms: str
    customer_urgency: str
    contact_preference: str
    category: str | None
    verified_priority: str | None
    assigned_support_user_id: UUID | None
    escalated: bool
    resolution_version: int
    resolution_summary: dict | None = None
    warranty: WarrantyInfo | None = None
    repair_jobs: list[RepairJobResponse] = []
    acknowledgments: list[AcknowledgmentResponse] = []
    idempotency_key: str
    created_at: datetime
    updated_at: datetime


class TriageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(pattern="^(inverter|panel|battery|mounting|wiring|monitoring|other)$")
    verified_priority: str = Field(pattern="^(low|normal|high|critical)$")
    note: str = Field(min_length=3, max_length=2000)


class SupportAssignmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    support_user_id: UUID
    note: str | None = Field(default=None, max_length=2000)


class RepairJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technician_user_id: UUID
    scheduled_starts_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)


class DiagnosticsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: str = Field(min_length=10, max_length=4000)
    root_cause: str | None = Field(default=None, max_length=2000)
    readings: dict | None = None


class WorkUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_performed: str = Field(min_length=10, max_length=4000)
    work_started_at: datetime
    work_finished_at: datetime
    parts_used: list[dict] = Field(default_factory=list)


class RepairSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=20, max_length=4000)


class InfoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=3, max_length=2000)


class CustomerReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=3, max_length=2000)


class ResolutionReady(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=20, max_length=4000)


class ConfirmationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(pattern="^(confirmed|disputed)$")
    summary_version: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=2000)


class ResolutionSummaryResponse(BaseModel):
    ticket_id: UUID
    reference: str
    status: str
    summary_version: int
    payload_hash: str
    summary: dict
    repair_job_id: UUID
    technician_user_id: UUID


class ReasonedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=2000)


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=3, max_length=2000)


class StaffEntry(BaseModel):
    user_id: UUID
    employee_code: str
    full_name: str
    role_code: str
    open_repair_jobs: int | None = None


class EscalationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=2000)
    verified_priority: str | None = Field(
        default=None, pattern="^(low|normal|high|critical)$"
    )
