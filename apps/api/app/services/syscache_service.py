"""SysCache: customer intelligence snapshots for support operations.

PostgreSQL is authoritative. ``phase4d_customer_snapshots`` is a
documented database-backed cache: scoped keys, TTL, schema/business
versioning, transactional-outbox invalidation, advisory-lock rebuilds
and explicit stale indicators with PostgreSQL fallback.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enquiry import CustomerSite
from app.models.identity import CustomerProfile, User
from app.models.phase3 import EquipmentSerial, InstallationJob, Warranty
from app.models.phase4d import (
    SYSCACHE_SCHEMA_VERSION,
    SYSCACHE_SCOPE_SUPPORT_OVERVIEW,
    CacheConsumerCursor,
    CacheMetric,
    CustomerSnapshotCache,
    SysCacheOutbox,
)
from app.models.support import ServiceTicket, TicketRepairJob
from app.models.workflow import SalesOrder

TENANT_DEFAULT = "default"
ALLOWED_SCOPES = (SYSCACHE_SCOPE_SUPPORT_OVERVIEW,)
CONSUMER_NAME = "syscache"

OUTAGE_MESSAGE = (
    "Snapshot cache is unavailable; this response was built live from "
    "PostgreSQL, which remains authoritative."
)


def cache_key(tenant: str, customer_id: uuid.UUID, scope: str) -> str:
    return f"{tenant}:{scope}:customer:{customer_id}"


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def compute_business_version(db: Session, customer_id: uuid.UUID) -> str:
    """Hash of the source rows feeding a snapshot.

    Any change to the customer's profile, sites, orders, serials,
    warranty, tickets or repair jobs changes this version, so readers
    can detect staleness without trusting the cached copy.
    """
    parts: list[str] = []
    profile = db.get(CustomerProfile, customer_id)
    parts.append(f"profile:{profile.full_name if profile else None}")
    site_ids = db.scalars(
        select(CustomerSite.id)
        .where(CustomerSite.customer_user_id == customer_id)
        .order_by(CustomerSite.id)
    ).all()
    parts.append(f"sites:{len(site_ids)}")
    orders = db.scalars(
        select(SalesOrder).where(SalesOrder.customer_user_id == customer_id)
    ).all()
    parts.append(f"orders:{[(str(o.id), o.package_code) for o in orders]}")
    serials = db.scalars(
        select(EquipmentSerial.serial_number, EquipmentSerial.status)
        .join(SalesOrder, SalesOrder.id == EquipmentSerial.order_id)
        .where(SalesOrder.customer_user_id == customer_id)
        .order_by(EquipmentSerial.serial_number)
    ).all()
    parts.append(f"serials:{[(s[0], s[1]) for s in serials]}")
    warranties = db.scalars(
        select(Warranty.status, Warranty.ends_at).where(
            Warranty.customer_user_id == customer_id
        )
    ).all()
    parts.append(f"warranties:{[(w[0], _iso(w[1])) for w in warranties]}")
    tickets = db.scalars(
        select(
            ServiceTicket.reference, ServiceTicket.status, ServiceTicket.resolution_version
        )
        .where(ServiceTicket.customer_user_id == customer_id)
        .order_by(ServiceTicket.reference)
    ).all()
    parts.append(f"tickets:{[(t[0], t[1], t[2]) for t in tickets]}")
    jobs = db.scalars(
        select(TicketRepairJob.reference, TicketRepairJob.status)
        .join(ServiceTicket, ServiceTicket.id == TicketRepairJob.ticket_id)
        .where(ServiceTicket.customer_user_id == customer_id)
        .order_by(TicketRepairJob.reference)
    ).all()
    parts.append(f"jobs:{[(j[0], j[1]) for j in jobs]}")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:32]


def build_snapshot_payload(db: Session, customer_id: uuid.UUID) -> dict[str, Any]:
    """Assemble a snapshot from authoritative PostgreSQL rows only."""
    profile = db.get(CustomerProfile, customer_id)
    if profile is None:
        raise AppError(404, "customer_not_found", "No customer profile for this user.")
    user = db.get(User, customer_id)
    sites = (
        db.scalars(
            select(CustomerSite).where(CustomerSite.customer_user_id == customer_id)
        ).all()
    )
    orders = (
        db.scalars(select(SalesOrder).where(SalesOrder.customer_user_id == customer_id))
    ).all()
    order_ids = [o.id for o in orders]
    serials: list[EquipmentSerial] = []
    jobs: list[InstallationJob] = []
    warranties: list[Warranty] = []
    if order_ids:
        serials = (
            db.scalars(
                select(EquipmentSerial).where(EquipmentSerial.order_id.in_(order_ids))
            ).all()
        )
        jobs = (
            db.scalars(
                select(InstallationJob).where(InstallationJob.order_id.in_(order_ids))
            ).all()
        )
        warranties = (
            db.scalars(select(Warranty).where(Warranty.order_id.in_(order_ids))).all()
        )
    tickets = (
        db.scalars(
            select(ServiceTicket).where(ServiceTicket.customer_user_id == customer_id)
        ).all()
    )
    ticket_ids = [t.id for t in tickets]
    repair_jobs: list[TicketRepairJob] = []
    if ticket_ids:
        repair_jobs = (
            db.scalars(
                select(TicketRepairJob).where(TicketRepairJob.ticket_id.in_(ticket_ids))
            ).all()
        )
    open_tickets = [t for t in tickets if t.status not in ("closed", "cancelled")]
    return {
        "customer": {
            "user_id": str(customer_id),
            "full_name": profile.full_name,
            "phone": profile.phone,
            "email": user.email if user else None,
        },
        "sites": [
            {
                "id": str(s.id),
                "line1": s.line1,
                "city": s.city,
                "state": s.state,
                "postal_code": s.postal_code,
            }
            for s in sites
        ],
        "orders": [
            {
                "id": str(o.id),
                "reference": o.reference,
                "package_code": o.package_code,
                "status": o.status,
                "total_minor": o.total_minor,
                "currency_code": o.currency_code,
            }
            for o in orders
        ],
        "installations": [
            {
                "id": str(j.id),
                "reference": j.reference,
                "order_id": str(j.order_id),
                "status": j.status,
                "slot_starts_at": _iso(j.slot_starts_at),
            }
            for j in jobs
        ],
        "equipment": [
            {
                "id": str(s.id),
                "serial_number": s.serial_number,
                "component_code": s.component_code,
                "status": s.status,
                "order_id": str(s.order_id) if s.order_id else None,
            }
            for s in serials
        ],
        "warranty": [
            {
                "order_id": str(w.order_id),
                "status": w.status,
                "starts_at": _iso(w.starts_at),
                "ends_at": _iso(w.ends_at),
                "coverage_note": w.coverage_note,
            }
            for w in warranties
        ],
        "tickets": {
            "open": [
                {
                    "id": str(t.id),
                    "reference": t.reference,
                    "status": t.status,
                    "category": t.category,
                    "verified_priority": t.verified_priority,
                    "customer_urgency": t.customer_urgency,
                    "fault_code": t.fault_code,
                }
                for t in open_tickets
            ],
            "history": [
                {
                    "id": str(t.id),
                    "reference": t.reference,
                    "status": t.status,
                    "category": t.category,
                    "verified_priority": t.verified_priority,
                }
                for t in tickets
                if t.status in ("closed", "cancelled")
            ],
            "open_count": len(open_tickets),
            "total_count": len(tickets),
        },
        "repair_history": [
            {
                "id": str(j.id),
                "reference": j.reference,
                "ticket_id": str(j.ticket_id),
                "status": j.status,
                "summary": j.summary,
            }
            for j in repair_jobs
        ],
    }


def _bump_metric(db: Session, name: str) -> None:
    try:
        row = db.get(CacheMetric, name)
        if row is None:
            row = CacheMetric(name=name, value=1)
            db.add(row)
        else:
            row.value = row.value + 1
        db.flush()
    except SQLAlchemyError:
        db.rollback()


def _get_row(
    db: Session, tenant: str, customer_id: uuid.UUID, scope: str
) -> CustomerSnapshotCache | None:
    return db.scalar(
        select(CustomerSnapshotCache).where(
            CustomerSnapshotCache.tenant == tenant,
            CustomerSnapshotCache.customer_user_id == customer_id,
            CustomerSnapshotCache.scope == scope,
        )
    )


def rebuild_snapshot(
    db: Session,
    *,
    tenant: str,
    customer_id: uuid.UUID,
    scope: str,
    actor_id: uuid.UUID | None,
    ttl_seconds: int,
    now: datetime,
) -> CustomerSnapshotCache:
    """Rebuild under a per-key advisory lock so concurrent rebuilds collapse."""
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": cache_key(tenant, customer_id, scope)},
    )
    existing = _get_row(db, tenant, customer_id, scope)
    current_version = compute_business_version(db, customer_id)
    if (
        existing is not None
        and existing.invalidated_at is None
        and existing.business_version == current_version
        and existing.expires_at > now
    ):
        return existing
    payload = build_snapshot_payload(db, customer_id)
    if existing is None:
        existing = CustomerSnapshotCache(
            tenant=tenant,
            customer_user_id=customer_id,
            scope=scope,
            schema_version=SYSCACHE_SCHEMA_VERSION,
            business_version=current_version,
            payload=payload,
            generated_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            built_by_user_id=actor_id,
        )
        db.add(existing)
    else:
        existing.schema_version = SYSCACHE_SCHEMA_VERSION
        existing.business_version = current_version
        existing.payload = payload
        existing.generated_at = now
        existing.expires_at = now + timedelta(seconds=ttl_seconds)
        existing.invalidated_at = None
        existing.built_by_user_id = actor_id
    db.flush()
    _bump_metric(db, "rebuilds")
    return existing


def get_snapshot(
    db: Session,
    *,
    tenant: str,
    customer_id: uuid.UUID,
    scope: str,
    actor_id: uuid.UUID | None,
    ttl_seconds: int,
    force_fallback: bool = False,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Serve a snapshot with explicit source/staleness metadata."""
    if scope not in ALLOWED_SCOPES:
        raise AppError(400, "invalid_scope", f"Unknown snapshot scope {scope!r}.")
    started = time.perf_counter()
    now = datetime.now(UTC)
    current_version: str | None = None
    try:
        current_version = compute_business_version(db, customer_id)
    except AppError:
        raise
    except SQLAlchemyError as exc:
        raise AppError(503, "snapshot_source_failed", str(exc)) from exc

    def _format(
        row: CustomerSnapshotCache | None,
        *,
        source: str,
        stale: bool,
        stale_reason: str | None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        body = payload if payload is not None else (row.payload if row else {})
        generated = _iso(row.generated_at) if row else _iso(now)
        expires = _iso(row.expires_at) if row else _iso(now)
        return {
            "cache_key": cache_key(tenant, customer_id, scope),
            "scope": scope,
            "source": source,
            "stale": stale,
            "stale_reason": stale_reason,
            "schema_version": row.schema_version if row else SYSCACHE_SCHEMA_VERSION,
            "business_version": (
                row.business_version if row else (current_version or "unknown")
            ),
            "generated_at": generated,
            "expires_at": expires,
            "build_ms": round(elapsed_ms, 2),
            "snapshot": body,
        }

    if force_fallback:
        payload = build_snapshot_payload(db, customer_id)
        _bump_metric(db, "fallbacks")
        formatted = _format(None, source="postgresql-fallback", stale=False,
                            stale_reason="cache_bypassed_for_test_or_outage",
                            payload=payload)
        formatted["business_version"] = current_version or "unknown"
        return formatted

    try:
        row = _get_row(db, tenant, customer_id, scope)
    except SQLAlchemyError:
        db.rollback()
        payload = build_snapshot_payload(db, customer_id)
        _bump_metric(db, "fallbacks")
        formatted = _format(None, source="postgresql-fallback", stale=False,
                            stale_reason=OUTAGE_MESSAGE, payload=payload)
        formatted["business_version"] = current_version or "unknown"
        return formatted

    fresh = (
        row is not None
        and not force_refresh
        and row.invalidated_at is None
        and row.schema_version == SYSCACHE_SCHEMA_VERSION
        and row.business_version == current_version
        and row.expires_at > now
    )
    if fresh:
        assert row is not None
        _bump_metric(db, "hits")
        db.commit()
        return _format(row, source="cache", stale=False, stale_reason=None)

    if row is not None and row.schema_version != SYSCACHE_SCHEMA_VERSION:
        stale_reason: str | None = "schema_version_rollover"
    elif row is not None and row.invalidated_at is not None:
        stale_reason = "invalidated_by_event"
    elif row is not None and row.business_version != current_version:
        stale_reason = "business_version_changed"
    elif row is not None and row.expires_at <= now:
        stale_reason = "ttl_expired"
    else:
        stale_reason = "cold_miss" if row is None else None

    if not force_refresh and row is not None:
        _bump_metric(db, "misses")
    try:
        rebuilt = rebuild_snapshot(
            db,
            tenant=tenant,
            customer_id=customer_id,
            scope=scope,
            actor_id=actor_id,
            ttl_seconds=ttl_seconds,
            now=now,
        )
        db.commit()
    except AppError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        if row is not None:
            _bump_metric(db, "fallbacks")
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
            return _format(row, source="cache-stale", stale=True,
                           stale_reason="rebuild_failed_serving_stale")
        payload = build_snapshot_payload(db, customer_id)
        return _format(None, source="postgresql-fallback", stale=False,
                       stale_reason=OUTAGE_MESSAGE, payload=payload)
    if row is None:
        _bump_metric(db, "misses")
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
    return _format(
        rebuilt,
        source="cache-rebuilt",
        stale=False,
        stale_reason=(None if stale_reason == "cold_miss" else stale_reason),
    )


def emit_invalidation(
    db: Session,
    *,
    event_id: uuid.UUID,
    aggregate_kind: str,
    aggregate_id: str,
    customer_id: uuid.UUID | None,
    occurred_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
) -> SysCacheOutbox:
    """Append an invalidation event idempotently (same transaction as change).

    This is the Phase 4C integration contract: finance/payment writers
    call this alongside their postings with ``aggregate_kind="finance"``
    (or ``"payment"``) so SysCache invalidates without merging branches.
    """
    if aggregate_kind not in (
        "ticket", "order", "payment", "serial", "warranty", "repair", "finance",
    ):
        raise AppError(400, "invalid_aggregate_kind", "Unknown aggregate kind.")
    event = SysCacheOutbox(
        event_id=event_id,
        aggregate_kind=aggregate_kind,
        aggregate_id=aggregate_id,
        customer_user_id=customer_id,
        occurred_at=occurred_at or datetime.now(UTC),
        payload=payload or {},
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(SysCacheOutbox).where(SysCacheOutbox.event_id == event_id)
        )
        if existing is None:
            raise
        return existing
    return event


def drain_outbox(db: Session, consumer_name: str = CONSUMER_NAME, limit: int = 500) -> dict[str, Any]:
    """Apply pending outbox events: mark affected snapshots invalidated.

    Monotonic and idempotent: a snapshot newer than the event is left
    alone, so late or out-of-order events can never roll a snapshot back
    to older data -- they only ever mark it stale.
    """
    cursor = db.get(CacheConsumerCursor, consumer_name)
    if cursor is None:
        cursor = CacheConsumerCursor(consumer_name=consumer_name, last_event_id=0)
        db.add(cursor)
        db.flush()
    events = db.scalars(
        select(SysCacheOutbox)
        .where(SysCacheOutbox.id > cursor.last_event_id)
        .order_by(SysCacheOutbox.id)
        .limit(limit)
    ).all()
    applied = 0
    skipped_stale_event = 0
    max_id = cursor.last_event_id
    for event in events:
        max_id = max(max_id, event.id)
        if event.customer_user_id is None:
            continue
        rows = db.scalars(
            select(CustomerSnapshotCache).where(
                CustomerSnapshotCache.customer_user_id == event.customer_user_id
            )
        ).all()
        for row in rows:
            generated = row.generated_at
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=UTC)
            occurred = event.occurred_at
            if occurred.tzinfo is None:
                occurred = occurred.replace(tzinfo=UTC)
            if generated >= occurred and row.invalidated_at is None:
                skipped_stale_event += 1
                continue
            if row.invalidated_at is None:
                row.invalidated_at = occurred
                applied += 1
    cursor.last_event_id = max_id
    cursor.updated_at = datetime.now(UTC)
    db.flush()
    return {
        "consumer": consumer_name,
        "events_seen": len(events),
        "snapshots_invalidated": applied,
        "out_of_order_skipped": skipped_stale_event,
        "cursor": max_id,
    }


def cache_stats(db: Session) -> dict[str, Any]:
    metrics = {m.name: m.value for m in db.scalars(select(CacheMetric)).all()}
    total = db.scalar(select(func.count()).select_from(CustomerSnapshotCache)) or 0
    stale = db.scalar(
        select(func.count())
        .select_from(CustomerSnapshotCache)
        .where(CustomerSnapshotCache.invalidated_at.is_not(None))
    ) or 0
    return {
        "snapshots": total,
        "invalidated": stale,
        "hits": metrics.get("hits", 0),
        "misses": metrics.get("misses", 0),
        "rebuilds": metrics.get("rebuilds", 0),
        "fallbacks": metrics.get("fallbacks", 0),
    }
