"""Phase 4D intelligence records: SysCache snapshots, outbox, AI assists,
weather intelligence and verified generation readings.

All tables are additive. No existing table is altered here. PostgreSQL
remains the authoritative store; ``phase4d_customer_snapshots`` is a
documented database-backed cache with TTL semantics, schema/business
versioning and explicit stale indicators.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SYSCACHE_SCHEMA_VERSION = 1
SYSCACHE_SCOPE_SUPPORT_OVERVIEW = "support-overview"

OUTBOX_KINDS = (
    "ticket",
    "order",
    "payment",
    "serial",
    "warranty",
    "repair",
    "finance",
)

AI_MODES = ("deterministic", "provider")
AI_STATUSES = ("draft", "confirmed", "discarded", "rejected", "failed")

ADVISORY_KINDS = ("heavy_rain", "high_wind")
ADVISORY_STATUSES = ("open", "acknowledged", "dismissed")

READING_STATUSES = ("accepted", "rejected", "quarantined")


class CustomerSnapshotCache(Base):
    """Database-backed SysCache row for one (tenant, customer, scope).

    The payload is a point-in-time snapshot built from authoritative
    tables. ``business_version`` is a content hash of the source rows; a
    reader recomputes it to detect staleness without trusting the cache.
    """

    __tablename__ = "phase4d_customer_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "tenant", "customer_user_id", "scope", name="uq_phase4d_snapshots_key"
        ),
        Index("ix_phase4d_snapshots_customer", "customer_user_id", "scope"),
        Index("ix_phase4d_snapshots_expiry", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    customer_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_profiles.user_id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    business_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    built_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class SysCacheOutbox(Base):
    """Transactional outbox for cache invalidation events.

    Writers insert a row in the same transaction as their business change.
    The consumer (``drain_outbox``) advances a per-consumer cursor, so
    replays are idempotent and late/out-of-order events only ever mark
    snapshots stale -- they never refresh them with older data.
    """

    __tablename__ = "phase4d_cache_outbox"
    __table_args__ = (
        CheckConstraint(
            "aggregate_kind IN ('ticket', 'order', 'payment', 'serial', "
            "'warranty', 'repair', 'finance')",
            name="ck_phase4d_outbox_kind",
        ),
        Index("ix_phase4d_outbox_customer", "customer_user_id"),
        Index("ix_phase4d_outbox_occurred", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    aggregate_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_profiles.user_id")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class CacheConsumerCursor(Base):
    """Per-consumer outbox cursor for idempotent invalidation."""

    __tablename__ = "phase4d_cache_consumers"

    consumer_name: Mapped[str] = mapped_column(String(80), primary_key=True)
    last_event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CacheMetric(Base):
    """Durable cache counters (hits, misses, rebuilds, fallbacks)."""

    __tablename__ = "phase4d_cache_metrics"

    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class AiAssistSession(Base):
    """One AI-assistance interaction for a support ticket intake.

    ``draft`` is machine output validated against a strict schema. It is
    never applied to a ticket automatically: a ``confirmed`` row records
    the human operator, timestamp and any edits. ``input_text`` is not
    stored -- only its hash -- so raw complaints live solely on tickets.
    """

    __tablename__ = "phase4d_ai_assists"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('deterministic', 'provider')", name="ck_phase4d_ai_mode"
        ),
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'discarded', 'rejected', 'failed')",
            name="ck_phase4d_ai_status",
        ),
        Index("ix_phase4d_ai_ticket", "ticket_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_tickets.id")
    )
    customer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customer_profiles.user_id")
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    draft: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_note: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SiteGeolocation(Base):
    """Verified coordinates for a customer site.

    Weather intelligence only runs for sites with ``verified=True``;
    unverified rows keep coordinates quarantined from provider calls.
    """

    __tablename__ = "phase4d_site_geolocations"
    __table_args__ = (
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="ck_phase4d_geo_lat"
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="ck_phase4d_geo_lon"
        ),
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_sites.id"), primary_key=True
    )
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id")
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ForecastSnapshot(Base):
    """One provider forecast response stored verbatim with provenance."""

    __tablename__ = "phase4d_forecast_snapshots"
    __table_args__ = (
        Index("ix_phase4d_forecast_site", "site_id", "fetched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_sites.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    request_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    units: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class WeatherAdvisory(Base):
    """Advisory derived from a stored forecast; never reschedules work."""

    __tablename__ = "phase4d_weather_advisories"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('heavy_rain', 'high_wind')", name="ck_phase4d_advisory_kind"
        ),
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'dismissed')",
            name="ck_phase4d_advisory_status",
        ),
        UniqueConstraint(
            "forecast_id", "kind", name="uq_phase4d_advisory_forecast_kind"
        ),
        Index("ix_phase4d_advisory_site", "site_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_sites.id"), nullable=False
    )
    forecast_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("phase4d_forecast_snapshots.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    window_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id")
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GenerationReading(Base):
    """One authenticated device/provider measurement.

    ``(device_ref, event_id)`` is the provider deduplication key: a
    retried ingest returns the original row instead of double-counting.
    Rows are immutable; corrections arrive as new events.
    """

    __tablename__ = "phase4d_generation_readings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('accepted', 'rejected', 'quarantined')",
            name="ck_phase4d_reading_status",
        ),
        UniqueConstraint(
            "device_ref", "event_id", name="uq_phase4d_readings_device_event"
        ),
        Index("ix_phase4d_readings_order", "order_id", "measured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_orders.id"), nullable=False
    )
    device_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    event_id: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    energy_wh: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    power_w: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="Wh")
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(240))
    received_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
