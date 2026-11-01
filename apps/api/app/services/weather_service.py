"""Weather-aware solar operations (Phase 4D).

Every forecast stores provider, fetched/issued timestamps, validity and
units. Without a configured provider the capability reports UNAVAILABLE
-- forecasts are never simulated. Advisories flag heavy rain and high
wind; acknowledging them never reschedules work. Appointment changes
must go through the authorized scheduling flows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enquiry import CustomerSite
from app.models.phase3 import InstallationJob
from app.models.phase4d import ForecastSnapshot, SiteGeolocation, WeatherAdvisory
from app.models.support import ServiceTicket, TicketRepairJob
from app.models.workflow import SalesOrder, Survey

PROVIDER_TIMEOUT_SECONDS = 10.0
FORECAST_VALIDITY_HOURS = 24
HEAVY_RAIN_MM_PER_H = 20.0
HIGH_WIND_MS = 17.0


class ForecastPayloadError(AppError):
    def __init__(self, message: str):
        super().__init__(502, "weather_bad_payload", message)


class WeatherProvider(Protocol):
    name: str

    def fetch(self, latitude: float, longitude: float) -> dict[str, Any]: ...


class UnavailableProvider:
    name = "unavailable"

    def fetch(self, latitude: float, longitude: float) -> dict[str, Any]:
        raise AppError(
            503,
            "weather_unavailable",
            "No weather provider is configured; forecasts are unavailable, not simulated.",
        )


class HttpWeatherProvider:
    """Bounded HTTP provider expecting a documented JSON forecast shape.

    Expected response (JSON)::

        {"issued_at": "<iso>",
         "units": "metric",
         "periods": [{"starts_at": "<iso>", "rain_mm_per_h": 0.0, "wind_ms": 0.0}]}
    """

    name = "http"

    def __init__(self, base_url: str, api_key: str = "", timeout: float = PROVIDER_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def fetch(self, latitude: float, longitude: float) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = httpx.get(
                f"{self.base_url}/forecast",
                params={"lat": latitude, "lon": longitude},
                headers=headers,
                timeout=self.timeout,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise AppError(503, "weather_provider_timeout",
                           "Weather provider did not respond in time.") from exc
        if response.status_code != 200:
            raise AppError(502, "weather_provider_error",
                           f"Weather provider returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AppError(502, "weather_provider_error",
                           "Weather provider returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise AppError(502, "weather_provider_error",
                           "Weather provider returned a non-object.")
        return payload


def resolve_provider(settings: Any) -> WeatherProvider:
    url = getattr(settings, "weather_provider_url", None)
    if not url:
        return UnavailableProvider()
    override = getattr(settings, "_weather_provider_override", None)
    if override is not None:
        return override
    key = getattr(settings, "weather_provider_key", None) or ""
    provider = HttpWeatherProvider(url, key)
    provider.name = getattr(settings, "weather_provider_name", None) or "http"
    return provider


def _parse_iso(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ForecastPayloadError(f"Forecast field {field!r} must be an ISO timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ForecastPayloadError(f"Forecast field {field!r} is not a timestamp.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_forecast(payload: dict[str, Any], *, provider_name: str) -> dict[str, Any]:
    issued_at = _parse_iso(payload.get("issued_at"), "issued_at")
    units = payload.get("units", "metric")
    if not isinstance(units, str):
        raise ForecastPayloadError("Forecast field 'units' must be a string.")
    raw_periods = payload.get("periods")
    if not isinstance(raw_periods, list) or not raw_periods:
        raise ForecastPayloadError("Forecast must include a non-empty 'periods' list.")
    periods = []
    for entry in raw_periods:
        if not isinstance(entry, dict):
            raise ForecastPayloadError("Each forecast period must be an object.")
        starts_at = _parse_iso(entry.get("starts_at"), "periods[].starts_at")
        try:
            rain = float(entry.get("rain_mm_per_h", 0.0))
            wind = float(entry.get("wind_ms", 0.0))
        except (TypeError, ValueError) as exc:
            raise ForecastPayloadError("Rain and wind values must be numbers.") from exc
        if rain < 0 or wind < 0:
            raise ForecastPayloadError("Rain and wind values must be non-negative.")
        periods.append({"starts_at": starts_at, "rain_mm_per_h": rain, "wind_ms": wind})
    periods.sort(key=lambda p: p["starts_at"])
    return {
        "provider": provider_name,
        "issued_at": issued_at,
        "units": units,
        "periods": periods,
        "valid_from": periods[0]["starts_at"],
        "valid_to": periods[-1]["starts_at"] + timedelta(hours=3),
    }


def verified_geolocation(db: Session, site_id: uuid.UUID) -> SiteGeolocation:
    site = db.get(CustomerSite, site_id)
    if site is None:
        raise AppError(404, "site_not_found", "Customer site does not exist.")
    geo = db.get(SiteGeolocation, site_id)
    if geo is None or not geo.verified:
        raise AppError(
            422, "site_location_unverified",
            "Site has no verified coordinates; weather intelligence is unavailable for it.",
        )
    return geo


def fetch_and_store_forecast(
    db: Session,
    settings: Any,
    *,
    site_id: uuid.UUID,
    request_id: str,
    actor_id: uuid.UUID,
) -> ForecastSnapshot:
    geo = verified_geolocation(db, site_id)
    provider = resolve_provider(settings)
    raw = provider.fetch(float(geo.latitude), float(geo.longitude))
    normalized = normalize_forecast(raw, provider_name=provider.name)
    now = datetime.now(UTC)
    snapshot = ForecastSnapshot(
        site_id=site_id,
        provider=provider.name,
        request_id=request_id,
        issued_at=normalized["issued_at"],
        fetched_at=now,
        valid_from=normalized["valid_from"],
        valid_to=normalized["valid_to"],
        units=normalized["units"],
        payload={
            "issued_at": normalized["issued_at"].isoformat(),
            "units": normalized["units"],
            "latitude": float(geo.latitude),
            "longitude": float(geo.longitude),
            "periods": [
                {
                    "starts_at": p["starts_at"].isoformat(),
                    "rain_mm_per_h": p["rain_mm_per_h"],
                    "wind_ms": p["wind_ms"],
                }
                for p in normalized["periods"]
            ],
        },
    )
    db.add(snapshot)
    db.flush()
    derive_advisories(db, snapshot=snapshot)
    db.flush()
    return snapshot


def derive_advisories(db: Session, *, snapshot: ForecastSnapshot) -> list[WeatherAdvisory]:
    created: list[WeatherAdvisory] = []
    periods = snapshot.payload.get("periods", [])
    worst_rain = max([p.get("rain_mm_per_h", 0.0) for p in periods] or [0.0])
    worst_wind = max([p.get("wind_ms", 0.0) for p in periods] or [0.0])
    candidates: list[tuple[str, str, str, float]] = []
    if worst_rain >= HEAVY_RAIN_MM_PER_H:
        candidates.append((
            "heavy_rain", "high",
            f"Heavy rain expected (peak {worst_rain:.1f} mm/h, threshold "
            f"{HEAVY_RAIN_MM_PER_H:.0f} mm/h). Outdoor electrical work is unsafe.",
            worst_rain,
        ))
    if worst_wind >= HIGH_WIND_MS:
        candidates.append((
            "high_wind", "high",
            f"High wind expected (peak {worst_wind:.1f} m/s, threshold "
            f"{HIGH_WIND_MS:.0f} m/s). Roof and panel-handling work is unsafe.",
            worst_wind,
        ))
    for kind, severity, summary, _peak in candidates:
        existing = db.scalar(
            select(WeatherAdvisory).where(
                WeatherAdvisory.forecast_id == snapshot.id,
                WeatherAdvisory.kind == kind,
            )
        )
        if existing is not None:
            created.append(existing)
            continue
        advisory = WeatherAdvisory(
            site_id=snapshot.site_id,
            forecast_id=snapshot.id,
            kind=kind,
            severity=severity,
            summary=summary,
            window_from=snapshot.valid_from,
            window_to=snapshot.valid_to,
        )
        db.add(advisory)
        created.append(advisory)
    return created


def forecast_freshness(snapshot: ForecastSnapshot, *, now: datetime) -> str:
    fetched = snapshot.fetched_at
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=UTC)
    valid_to = snapshot.valid_to
    if valid_to.tzinfo is None:
        valid_to = valid_to.replace(tzinfo=UTC)
    if now > valid_to:
        return "stale"
    return "fresh"


def affected_appointments(db: Session, *, site_id: uuid.UUID,
                          window_from: datetime, window_to: datetime) -> list[dict[str, Any]]:
    """Real scheduled visits overlapping an advisory window at this site."""
    affected: list[dict[str, Any]] = []
    surveys = db.scalars(
        select(Survey).where(
            Survey.site_id == site_id,
            Survey.appointment_starts_at.is_not(None),
            Survey.appointment_starts_at >= window_from,
            Survey.appointment_starts_at <= window_to,
        )
    ).all()
    for survey in surveys:
        affected.append({
            "kind": "survey",
            "id": str(survey.id),
            "reference": survey.reference,
            "starts_at": survey.appointment_starts_at.isoformat()
            if survey.appointment_starts_at else None,
        })
    order_ids = db.scalars(
        select(SalesOrder.id).where(SalesOrder.site_id == site_id)
    ).all()
    if order_ids:
        for job in db.scalars(
            select(InstallationJob).where(
                InstallationJob.order_id.in_(order_ids),
                InstallationJob.slot_starts_at.is_not(None),
                InstallationJob.slot_starts_at >= window_from,
                InstallationJob.slot_starts_at <= window_to,
                InstallationJob.status.not_in(("completed", "cancelled")),
            )
        ).all():
            affected.append({
                "kind": "installation",
                "id": str(job.id),
                "reference": job.reference,
                "starts_at": job.slot_starts_at.isoformat() if job.slot_starts_at else None,
            })
    site_order_ids = set(order_ids)
    repair_rows = db.execute(
        select(TicketRepairJob, ServiceTicket)
        .join(ServiceTicket, ServiceTicket.id == TicketRepairJob.ticket_id)
        .where(
            TicketRepairJob.scheduled_starts_at.is_not(None),
            TicketRepairJob.scheduled_starts_at >= window_from,
            TicketRepairJob.scheduled_starts_at <= window_to,
            TicketRepairJob.status.not_in(("work_submitted", "cancelled")),
        )
    ).all()
    for job, ticket in repair_rows:
        if ticket.site_id == site_id or ticket.order_id in site_order_ids:
            affected.append({
                "kind": "repair",
                "id": str(job.id),
                "reference": job.reference,
                "starts_at": job.scheduled_starts_at.isoformat()
                if job.scheduled_starts_at else None,
            })
    return affected


def acknowledge_advisory(
    db: Session, *, advisory_id: uuid.UUID, actor_id: uuid.UUID, action: str
) -> WeatherAdvisory:
    if action not in ("acknowledge", "dismiss"):
        raise AppError(400, "invalid_advisory_action",
                       "Action must be acknowledge or dismiss.")
    advisory = db.get(WeatherAdvisory, advisory_id)
    if advisory is None:
        raise AppError(404, "advisory_not_found", "Weather advisory does not exist.")
    if advisory.status != "open":
        raise AppError(409, "advisory_not_open", "Only open advisories can be actioned.")
    advisory.status = "acknowledged" if action == "acknowledge" else "dismissed"
    advisory.acknowledged_by_user_id = actor_id
    advisory.acknowledged_at = datetime.now(UTC)
    db.flush()
    return advisory


def upsert_geolocation(
    db: Session,
    *,
    site_id: uuid.UUID,
    latitude: Decimal | float,
    longitude: Decimal | float,
    verified: bool,
    actor_id: uuid.UUID,
    source: str = "manual",
) -> SiteGeolocation:
    site = db.get(CustomerSite, site_id)
    if site is None:
        raise AppError(404, "site_not_found", "Customer site does not exist.")
    lat, lon = float(latitude), float(longitude)
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise AppError(400, "invalid_coordinates", "Coordinates are out of range.")
    now = datetime.now(UTC)
    geo = db.get(SiteGeolocation, site_id)
    if geo is None:
        geo = SiteGeolocation(
            site_id=site_id, latitude=Decimal(str(lat)), longitude=Decimal(str(lon)),
            verified=verified, source=source,
            verified_by_user_id=actor_id if verified else None,
            verified_at=now if verified else None,
        )
        db.add(geo)
    else:
        geo.latitude = Decimal(str(lat))
        geo.longitude = Decimal(str(lon))
        geo.verified = verified
        geo.source = source
        geo.verified_by_user_id = actor_id if verified else None
        geo.verified_at = now if verified else None
    db.flush()
    return geo
