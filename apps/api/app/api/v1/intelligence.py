"""Phase 4D intelligence endpoints: SysCache, AI assists, weather, generation."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_settings
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.phase4d import SYSCACHE_SCOPE_SUPPORT_OVERVIEW, ForecastSnapshot
from app.schemas.phase4d import (
    AdvisoryAction,
    AdvisoryResponse,
    AssistConfirm,
    AssistCreate,
    AssistResponse,
    CacheMetricsResponse,
    EstimateResponse,
    ForecastFetch,
    ForecastResponse,
    GenerationSummaryResponse,
    GeolocationResponse,
    GeolocationUpsert,
    InvalidateRequest,
    InvalidateResponse,
    ReadingCreate,
    ReadingResponse,
    SnapshotResponse,
)
from app.services import ai_assist_service, generation_service, syscache_service, weather_service
from app.services.auth_service import assert_roles

router = APIRouter(tags=["intelligence"])

STAFF_INTELLIGENCE = {"support", "admin"}
OPS_ROLES = {"support", "admin", "technician"}


def _actor(user: User, allowed: set[str]) -> User:
    assert_roles(user, allowed)
    return user


def _assist_response(session) -> AssistResponse:
    return AssistResponse(
        id=session.id,
        ticket_id=session.ticket_id,
        customer_user_id=session.customer_user_id,
        mode=session.mode,
        model_provider=session.model_provider,
        model_version=session.model_version,
        status=session.status,
        draft=session.draft,
        created_at=session.created_at,
        expires_at=session.expires_at,
        confirmed_at=session.confirmed_at,
        confirmed_by_user_id=session.confirmed_by_user_id,
    )


def _snapshot_response(payload: dict) -> SnapshotResponse:
    return SnapshotResponse(**payload)


# ---------------------------------------------------------------- SysCache

@router.get("/customer-snapshots/{customer_id}", response_model=SnapshotResponse)
def read_snapshot(
    customer_id: UUID,
    scope: str = Query(default=SYSCACHE_SCOPE_SUPPORT_OVERVIEW),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> SnapshotResponse:
    if user.role_code == "customer" and user.id != customer_id:
        raise AppError(403, "snapshot_forbidden", "Customers can only view their own snapshot.")
    _actor(user, STAFF_INTELLIGENCE | {"customer"})
    payload = syscache_service.get_snapshot(
        db,
        tenant=syscache_service.TENANT_DEFAULT,
        customer_id=customer_id,
        scope=scope,
        actor_id=user.id,
        ttl_seconds=settings.syscache_ttl_seconds,
        force_fallback=settings.syscache_force_fallback,
    )
    return _snapshot_response(payload)


@router.post("/customer-snapshots/{customer_id}/refresh", response_model=SnapshotResponse)
def refresh_snapshot(
    customer_id: UUID,
    scope: str = Query(default=SYSCACHE_SCOPE_SUPPORT_OVERVIEW),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> SnapshotResponse:
    _actor(user, STAFF_INTELLIGENCE)
    payload = syscache_service.get_snapshot(
        db,
        tenant=syscache_service.TENANT_DEFAULT,
        customer_id=customer_id,
        scope=scope,
        actor_id=user.id,
        ttl_seconds=settings.syscache_ttl_seconds,
        force_refresh=True,
    )
    return _snapshot_response(payload)


@router.post("/cache/invalidate", response_model=InvalidateResponse)
def invalidate_cache(
    body: InvalidateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> InvalidateResponse:
    """Phase 4C integration contract: finance/payment writers emit events here.

    Idempotent on ``event_id``; the consumer cursor makes replays safe.
    """
    _actor(user, STAFF_INTELLIGENCE)
    syscache_service.emit_invalidation(
        db,
        event_id=body.event_id,
        aggregate_kind=body.aggregate_kind,
        aggregate_id=body.aggregate_id,
        customer_id=body.customer_user_id,
        occurred_at=body.occurred_at,
        payload=body.payload,
    )
    result = syscache_service.drain_outbox(db)
    db.commit()
    return InvalidateResponse(event_id=body.event_id, **result)


@router.get("/cache/metrics", response_model=CacheMetricsResponse)
def cache_metrics(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> CacheMetricsResponse:
    _actor(user, STAFF_INTELLIGENCE)
    return CacheMetricsResponse(**syscache_service.cache_stats(db))


# ------------------------------------------------------------- AI assists

@router.post("/ai-assists", response_model=AssistResponse)
def create_assist(
    body: AssistCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> AssistResponse:
    _actor(user, STAFF_INTELLIGENCE | {"customer"})
    ticket_customer: UUID | None = None
    if body.ticket_id is not None:
        from app.models.support import ServiceTicket  # noqa: PLC0415

        ticket = db.get(ServiceTicket, body.ticket_id)
        if ticket is None:
            raise AppError(404, "ticket_not_found", "Ticket does not exist.")
        ticket_customer = ticket.customer_user_id
        if user.role_code == "customer" and ticket.customer_user_id != user.id:
            raise AppError(403, "assist_forbidden", "Customers can only use assists on their own tickets.")
    customer_id = body.customer_user_id or ticket_customer
    if user.role_code == "customer":
        if customer_id is not None and customer_id != user.id:
            raise AppError(403, "assist_forbidden", "Customers can only use assists for themselves.")
        customer_id = user.id
    session = ai_assist_service.create_assist(
        db,
        settings,
        created_by=user.id,
        complaint_text=body.complaint_text,
        ticket_id=body.ticket_id,
        customer_id=customer_id,
        requested_mode=body.mode,
    )
    db.commit()
    db.refresh(session)
    return _assist_response(session)


@router.post("/ai-assists/{session_id}/confirm", response_model=AssistResponse)
def confirm_assist(
    session_id: UUID,
    body: AssistConfirm,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AssistResponse:
    _actor(user, STAFF_INTELLIGENCE)
    session = ai_assist_service.confirm_assist(
        db,
        session_id=session_id,
        actor_id=user.id,
        decision=body.decision,
        edited_summary=body.edited_summary,
        note=body.note,
    )
    db.commit()
    db.refresh(session)
    return _assist_response(session)


# ----------------------------------------------------------------- Weather

@router.post("/weather/sites/{site_id}/geolocation", response_model=GeolocationResponse)
def upsert_geolocation(
    site_id: UUID,
    body: GeolocationUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> GeolocationResponse:
    _actor(user, STAFF_INTELLIGENCE)
    geo = weather_service.upsert_geolocation(
        db,
        site_id=site_id,
        latitude=body.latitude,
        longitude=body.longitude,
        verified=body.verified,
        actor_id=user.id,
        source=body.source,
    )
    db.commit()
    db.refresh(geo)
    return GeolocationResponse(
        site_id=geo.site_id,
        latitude=float(geo.latitude),
        longitude=float(geo.longitude),
        verified=geo.verified,
        source=geo.source,
        verified_at=geo.verified_at,
    )


@router.post("/weather/forecasts", response_model=ForecastResponse)
def fetch_forecast(
    body: ForecastFetch,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> ForecastResponse:
    _actor(user, OPS_ROLES)
    try:
        snapshot = weather_service.fetch_and_store_forecast(
            db, settings, site_id=body.site_id, request_id=body.request_id,
            actor_id=user.id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        snapshot = db.scalar(
            select(ForecastSnapshot).where(ForecastSnapshot.request_id == body.request_id)
        )
        if snapshot is None:
            raise
    db.refresh(snapshot)
    now = datetime.now(UTC)
    return ForecastResponse(
        id=snapshot.id,
        site_id=snapshot.site_id,
        provider=snapshot.provider,
        request_id=snapshot.request_id,
        issued_at=snapshot.issued_at,
        fetched_at=snapshot.fetched_at,
        valid_from=snapshot.valid_from,
        valid_to=snapshot.valid_to,
        units=snapshot.units,
        freshness=weather_service.forecast_freshness(snapshot, now=now),
        payload=snapshot.payload,
    )


@router.get("/weather/advisories", response_model=list[AdvisoryResponse])
def list_advisories(
    site_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(open|acknowledged|dismissed)$"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[AdvisoryResponse]:
    _actor(user, OPS_ROLES)
    from app.models.phase4d import WeatherAdvisory  # noqa: PLC0415

    query = select(WeatherAdvisory).order_by(WeatherAdvisory.created_at.desc())
    if site_id is not None:
        query = query.where(WeatherAdvisory.site_id == site_id)
    if status is not None:
        query = query.where(WeatherAdvisory.status == status)
    now = datetime.now(UTC)
    responses: list[AdvisoryResponse] = []
    for advisory in db.scalars(query.limit(200)).all():
        affected = weather_service.affected_appointments(
            db, site_id=advisory.site_id,
            window_from=advisory.window_from, window_to=advisory.window_to,
        )
        responses.append(AdvisoryResponse(
            id=advisory.id,
            site_id=advisory.site_id,
            forecast_id=advisory.forecast_id,
            kind=advisory.kind,
            severity=advisory.severity,
            summary=advisory.summary,
            window_from=advisory.window_from,
            window_to=advisory.window_to,
            status=advisory.status,
            acknowledged_at=advisory.acknowledged_at,
            affected_appointments=affected,
        ))
    _ = now
    return responses


@router.post("/weather/advisories/{advisory_id}/ack", response_model=AdvisoryResponse)
def ack_advisory(
    advisory_id: UUID,
    body: AdvisoryAction,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> AdvisoryResponse:
    _actor(user, OPS_ROLES)
    advisory = weather_service.acknowledge_advisory(
        db, advisory_id=advisory_id, actor_id=user.id, action=body.action)
    db.commit()
    db.refresh(advisory)
    affected = weather_service.affected_appointments(
        db, site_id=advisory.site_id,
        window_from=advisory.window_from, window_to=advisory.window_to,
    )
    return AdvisoryResponse(
        id=advisory.id,
        site_id=advisory.site_id,
        forecast_id=advisory.forecast_id,
        kind=advisory.kind,
        severity=advisory.severity,
        summary=advisory.summary,
        window_from=advisory.window_from,
        window_to=advisory.window_to,
        status=advisory.status,
        acknowledged_at=advisory.acknowledged_at,
        affected_appointments=affected,
    )


@router.get("/weather/availability")
def weather_availability(
    user: User = Depends(current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    _actor(user, OPS_ROLES | {"customer"})
    provider = weather_service.resolve_provider(settings)
    return {
        "available": not isinstance(provider, weather_service.UnavailableProvider),
        "provider": provider.name,
    }


# --------------------------------------------------------------- Generation

@router.get("/generation/estimates", response_model=EstimateResponse)
def generation_estimate(
    order_id: UUID = Query(),
    scenario: str = Query(default="expected"),
    interval: str = Query(default="day"),
    month: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> EstimateResponse:
    order = generation_service.assert_order_visible(
        db, order_id=order_id, user_id=user.id, role_code=user.role_code)
    if user.role_code == "customer" and order.customer_user_id != user.id:
        raise AppError(403, "order_forbidden", "You can only view your own orders.")
    _actor(user, STAFF_INTELLIGENCE | {"customer"})
    result = generation_service.estimate_generation(
        db, order_id=order_id, scenario=scenario, interval=interval, month=month)
    return EstimateResponse(**result)


@router.get("/generation/summary", response_model=GenerationSummaryResponse)
def generation_summary(
    order_id: UUID = Query(),
    scenario: str = Query(default="expected"),
    interval: str = Query(default="day"),
    month: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> GenerationSummaryResponse:
    order = generation_service.assert_order_visible(
        db, order_id=order_id, user_id=user.id, role_code=user.role_code)
    if user.role_code == "customer" and order.customer_user_id != user.id:
        raise AppError(403, "order_forbidden", "You can only view your own orders.")
    _actor(user, STAFF_INTELLIGENCE | {"customer"})
    result = generation_service.generation_summary(
        db, order_id=order_id, scenario=scenario, interval=interval, month=month)
    return GenerationSummaryResponse(**result)


@router.post("/generation/readings", response_model=ReadingResponse)
def ingest_reading(
    body: ReadingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> ReadingResponse:
    _actor(user, STAFF_INTELLIGENCE | {"technician"})
    row, duplicate = generation_service.ingest_reading(
        db,
        order_id=body.order_id,
        device_ref=body.device_ref,
        event_id=body.event_id,
        source=body.source,
        measured_at=body.measured_at,
        energy_wh=body.energy_wh,
        power_w=body.power_w,
        actor_id=user.id,
    )
    db.commit()
    db.refresh(row)
    return ReadingResponse(
        id=row.id,
        order_id=row.order_id,
        device_ref=row.device_ref,
        event_id=row.event_id,
        source=row.source,
        measured_at=row.measured_at,
        energy_wh=row.energy_wh,
        power_w=row.power_w,
        unit=row.unit,
        status=row.status,
        rejection_reason=row.rejection_reason,
        duplicate=duplicate,
    )


@router.get("/generation/readings", response_model=list[ReadingResponse])
def list_readings(
    order_id: UUID = Query(),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list[ReadingResponse]:
    order = generation_service.assert_order_visible(
        db, order_id=order_id, user_id=user.id, role_code=user.role_code)
    if user.role_code == "customer" and order.customer_user_id != user.id:
        raise AppError(403, "order_forbidden", "You can only view your own orders.")
    _actor(user, STAFF_INTELLIGENCE | {"customer", "technician"})
    rows = generation_service.readings_for_order(db, order_id=order_id, status=status)
    return [
        ReadingResponse(
            id=row.id, order_id=row.order_id, device_ref=row.device_ref,
            event_id=row.event_id, source=row.source, measured_at=row.measured_at,
            energy_wh=row.energy_wh, power_w=row.power_w, unit=row.unit,
            status=row.status, rejection_reason=row.rejection_reason, duplicate=False,
        )
        for row in rows
    ]
