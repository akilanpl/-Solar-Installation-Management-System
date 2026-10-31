"""Solar generation intelligence (Phase 4D).

Estimates are documented engineering calculations, always labeled with
model version, assumptions, interval and units -- never presented as
measured generation. Verified readings arrive through an authenticated
ingestion boundary (source identity, meter/device reference, measured
timestamp, units, provider event ID) with duplicate rejection and
quarantine for invalid input.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.audit import SolarPackage
from app.models.phase4d import GenerationReading
from app.models.workflow import SalesOrder, Survey

ESTIMATE_MODEL = "pvest-v1"

# Mean daily peak-sun-hours by month for Indian latitudes, documented
# approximation for planning scenarios (kWh/kWp/day). Source label is
# part of every estimate response.
PSH_BY_MONTH: dict[int, float] = {
    1: 4.6, 2: 5.2, 3: 5.9, 4: 6.2, 5: 6.0, 6: 5.0,
    7: 4.3, 8: 4.2, 9: 4.8, 10: 5.3, 11: 4.9, 12: 4.5,
}
PSH_SOURCE = "pvest-v1 built-in India mean-PSH table (planning approximation)"

LOSS_ASSUMPTIONS: dict[str, float] = {
    "soiling": 0.97,
    "temperature": 0.90,
    "inverter": 0.96,
    "wiring": 0.98,
    "mismatch_misc": 0.93,
}
SCENARIOS = ("conservative", "expected", "optimistic")
SCENARIO_FACTOR = {"conservative": 0.9, "expected": 1.0, "optimistic": 1.1}
INTERVALS = ("day", "month", "year")

CLOCK_SKEW_TOLERANCE = timedelta(minutes=15)
MAX_READING_AGE_DAYS = 400


def _performance_ratio() -> float:
    value = 1.0
    for factor in LOSS_ASSUMPTIONS.values():
        value *= factor
    return round(value, 4)


def orientation_factor(*, azimuth_deg: float | None, tilt_deg: float | None,
                       latitude: float | None = None) -> tuple[float, str]:
    """Documented derate for non-ideal orientation, clamped to [0.7, 1.0]."""
    optimal_tilt = round(latitude, 1) if latitude is not None else 15.0
    tilt = tilt_deg if tilt_deg is not None else optimal_tilt
    azimuth = azimuth_deg if azimuth_deg is not None else 180.0
    factor = 1.0 - 0.003 * abs(tilt - optimal_tilt) - 0.0008 * abs(azimuth - 180.0)
    clamped = max(0.7, min(1.0, factor))
    basis = (
        f"tilt {tilt}deg vs optimal {optimal_tilt}deg, azimuth {azimuth}deg "
        f"vs due-south 180deg; linear derate clamped to [0.7, 1.0]"
    )
    return round(clamped, 4), basis


def estimate_generation(
    db: Session,
    *,
    order_id: uuid.UUID,
    scenario: str = "expected",
    interval: str = "day",
    month: int | None = None,
    latitude: float | None = None,
) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise AppError(400, "invalid_scenario", "Scenario must be conservative, expected or optimistic.")
    if interval not in INTERVALS:
        raise AppError(400, "invalid_interval", "Interval must be day, month or year.")
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "order_not_found", "Sales order does not exist.")
    package = db.scalar(select(SolarPackage).where(SolarPackage.code == order.package_code))
    capacity_w = package.capacity_w if package and package.capacity_w else None
    if capacity_w is None:
        raise AppError(422, "capacity_unknown",
                       "Package capacity is unknown; no estimate can be computed.")
    survey = db.get(Survey, order.survey_id)
    azimuth = float(survey.azimuth_deg) if survey and survey.azimuth_deg is not None else None
    tilt = float(survey.tilt_deg) if survey and survey.tilt_deg is not None else None
    month_value = month or datetime.now(UTC).month
    if month_value < 1 or month_value > 12:
        raise AppError(400, "invalid_month", "Month must be 1-12.")
    psh = PSH_BY_MONTH[month_value]
    orient, orient_basis = orientation_factor(azimuth_deg=azimuth, tilt_deg=tilt, latitude=latitude)
    pr = _performance_ratio()
    capacity_kw = capacity_w / 1000.0
    daily_kwh = capacity_kw * psh * pr * orient * SCENARIO_FACTOR[scenario]
    days = {"day": 1, "month": 30, "year": 365}[interval]
    energy_kwh = round(daily_kwh * days, 2)
    return {
        "kind": "estimate",
        "order_id": str(order_id),
        "model": ESTIMATE_MODEL,
        "scenario": scenario,
        "interval": interval,
        "month": month_value,
        "unit": "kWh",
        "energy_kwh": energy_kwh,
        "inputs": {
            "capacity_w": capacity_w,
            "package_code": order.package_code,
            "azimuth_deg": azimuth,
            "tilt_deg": tilt,
            "latitude": latitude,
            "peak_sun_hours_per_day": psh,
            "performance_ratio": pr,
            "orientation_factor": orient,
            "scenario_factor": SCENARIO_FACTOR[scenario],
        },
        "assumptions": {
            "irradiation": PSH_SOURCE,
            "losses": LOSS_ASSUMPTIONS,
            "orientation": orient_basis,
            "note": "Planning estimate only. This is not measured generation.",
        },
    }


def ingest_reading(
    db: Session,
    *,
    order_id: uuid.UUID,
    device_ref: str,
    event_id: str,
    source: str,
    measured_at: datetime,
    energy_wh: Decimal | float,
    power_w: Decimal | float | None,
    actor_id: uuid.UUID,
) -> tuple[GenerationReading, bool]:
    """Ingest one device measurement. Returns (row, duplicate).

    Duplicates on (device_ref, event_id) return the original row so
    retries never double-count. Invalid input is quarantined or rejected
    with reasons; nothing silently invents generation.
    """
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "order_not_found", "Sales order does not exist.")
    for label, value, limit in (("device_ref", device_ref, 80), ("event_id", event_id, 80),
                                ("source", source, 80)):
        if not value or not str(value).strip() or len(str(value)) > limit:
            raise AppError(400, "invalid_reading_field", f"{label} must be 1-{limit} characters.")
    if measured_at.tzinfo is None:
        measured_at = measured_at.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    try:
        energy = Decimal(str(energy_wh))
    except Exception as exc:
        raise AppError(400, "invalid_reading_field", "energy_wh must be numeric.") from exc
    power = None
    if power_w is not None:
        try:
            power = Decimal(str(power_w))
        except Exception as exc:
            raise AppError(400, "invalid_reading_field", "power_w must be numeric.") from exc
    existing = db.scalar(
        select(GenerationReading).where(
            GenerationReading.device_ref == device_ref,
            GenerationReading.event_id == event_id,
        )
    )
    if existing is not None:
        return existing, True
    status = "accepted"
    reason: str | None = None
    if energy < 0 or (power is not None and power < 0):
        status, reason = "quarantined", "negative energy or power value"
    elif measured_at > now + CLOCK_SKEW_TOLERANCE:
        status, reason = "rejected", "measured_at is in the future beyond clock-skew tolerance"
    elif measured_at < now - timedelta(days=MAX_READING_AGE_DAYS):
        status, reason = "rejected", "measured_at is older than the accepted history window"
    row = GenerationReading(
        order_id=order_id,
        device_ref=device_ref.strip(),
        event_id=event_id.strip(),
        source=source.strip(),
        measured_at=measured_at,
        energy_wh=energy,
        power_w=power,
        unit="Wh",
        status=status,
        rejection_reason=reason,
        received_by_user_id=actor_id,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(GenerationReading).where(
                GenerationReading.device_ref == device_ref,
                GenerationReading.event_id == event_id,
            )
        )
        if existing is None:
            raise
        return existing, True
    return row, False


def readings_for_order(db: Session, *, order_id: uuid.UUID,
                       status: str | None = None) -> list[GenerationReading]:
    query = select(GenerationReading).where(GenerationReading.order_id == order_id)
    if status is not None:
        if status not in ("accepted", "rejected", "quarantined"):
            raise AppError(400, "invalid_status", "Unknown reading status.")
        query = query.where(GenerationReading.status == status)
    return list(db.scalars(query.order_by(GenerationReading.measured_at.desc())).all())


def generation_summary(db: Session, *, order_id: uuid.UUID, **estimate_kwargs: Any) -> dict[str, Any]:
    estimate = estimate_generation(db, order_id=order_id, **estimate_kwargs)
    readings = readings_for_order(db, order_id=order_id, status="accepted")
    total_wh = sum((r.energy_wh for r in readings), Decimal("0"))
    latest = readings[0] if readings else None
    return {
        "estimate": estimate,
        "verified": {
            "reading_count": len(readings),
            "total_energy_kwh": round(float(total_wh) / 1000.0, 3),
            "latest_measured_at": latest.measured_at.isoformat() if latest else None,
            "latest_source": latest.source if latest else None,
            "unavailable": len(readings) == 0,
            "unavailable_reason": (
                "No authenticated device or provider readings exist for this order."
                if not readings else None
            ),
        },
    }


def assert_order_visible(db: Session, *, order_id: uuid.UUID, user_id: uuid.UUID,
                         role_code: str) -> SalesOrder:
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "order_not_found", "Sales order does not exist.")
    if role_code == "customer" and order.customer_user_id != user_id:
        raise AppError(403, "order_forbidden", "You can only view your own orders.")
    return order
