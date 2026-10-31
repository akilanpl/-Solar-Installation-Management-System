"""Phase 4D request/response contracts."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SnapshotResponse(BaseModel):
    cache_key: str
    scope: str
    source: str
    stale: bool
    stale_reason: str | None
    schema_version: int
    business_version: str
    generated_at: str | None
    expires_at: str | None
    build_ms: float
    snapshot: dict


class InvalidateRequest(BaseModel):
    event_id: UUID
    aggregate_kind: str = Field(pattern="^(ticket|order|payment|serial|warranty|repair|finance)$")
    aggregate_id: str = Field(min_length=1, max_length=80)
    customer_user_id: UUID | None = None
    occurred_at: datetime | None = None
    payload: dict = Field(default_factory=dict)


class InvalidateResponse(BaseModel):
    event_id: UUID
    consumer: str
    events_seen: int
    snapshots_invalidated: int
    out_of_order_skipped: int
    cursor: int


class CacheMetricsResponse(BaseModel):
    snapshots: int
    invalidated: int
    hits: int
    misses: int
    rebuilds: int
    fallbacks: int


class AssistCreate(BaseModel):
    complaint_text: str = Field(min_length=1, max_length=4000)
    ticket_id: UUID | None = None
    customer_user_id: UUID | None = None
    mode: str = Field(default="auto", pattern="^(auto|deterministic|provider)$")


class AssistResponse(BaseModel):
    id: UUID
    ticket_id: UUID | None
    customer_user_id: UUID | None
    mode: str
    model_provider: str
    model_version: str
    status: str
    draft: dict
    created_at: datetime
    expires_at: datetime
    confirmed_at: datetime | None
    confirmed_by_user_id: UUID | None


class AssistConfirm(BaseModel):
    decision: str = Field(pattern="^(confirmed|discarded)$")
    edited_summary: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=500)


class GeolocationUpsert(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    verified: bool = False
    source: str = Field(default="manual", max_length=80)


class GeolocationResponse(BaseModel):
    site_id: UUID
    latitude: float
    longitude: float
    verified: bool
    source: str
    verified_at: datetime | None


class ForecastFetch(BaseModel):
    site_id: UUID
    request_id: str = Field(min_length=8, max_length=80)


class ForecastResponse(BaseModel):
    id: UUID
    site_id: UUID
    provider: str
    request_id: str
    issued_at: datetime
    fetched_at: datetime
    valid_from: datetime
    valid_to: datetime
    units: str
    freshness: str
    payload: dict


class AdvisoryResponse(BaseModel):
    id: UUID
    site_id: UUID
    forecast_id: UUID
    kind: str
    severity: str
    summary: str
    window_from: datetime
    window_to: datetime
    status: str
    acknowledged_at: datetime | None
    affected_appointments: list[dict] = Field(default_factory=list)


class AdvisoryAction(BaseModel):
    action: str = Field(pattern="^(acknowledge|dismiss)$")


class EstimateResponse(BaseModel):
    kind: str
    order_id: UUID
    model: str
    scenario: str
    interval: str
    month: int
    unit: str
    energy_kwh: float
    inputs: dict
    assumptions: dict


class ReadingCreate(BaseModel):
    order_id: UUID
    device_ref: str = Field(min_length=1, max_length=80)
    event_id: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=80)
    measured_at: datetime
    energy_wh: Decimal
    power_w: Decimal | None = None


class ReadingResponse(BaseModel):
    id: UUID
    order_id: UUID
    device_ref: str
    event_id: str
    source: str
    measured_at: datetime
    energy_wh: Decimal
    power_w: Decimal | None
    unit: str
    status: str
    rejection_reason: str | None
    duplicate: bool = False


class GenerationSummaryResponse(BaseModel):
    estimate: dict
    verified: dict
