"""Phase 4D intelligence records: SysCache, AI assists, weather, generation.

Revision ID: 4d1a2b3c4d50
Revises: 4b1c2d3e4f51

Additive only: creates eight new tables, touches no existing ones.
If Phase 4C creates a parallel head, reconcile ancestry by merging
heads at integration time -- never by rewriting this revision.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "4d1a2b3c4d50"
down_revision = "4b1c2d3e4f51"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("phase4d_customer_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant", sa.String(64), nullable=False, server_default="default"),
        sa.Column("customer_user_id", sa.Uuid(), sa.ForeignKey("customer_profiles.user_id"), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("business_version", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("built_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("tenant", "customer_user_id", "scope", name="uq_phase4d_snapshots_key"),
    )
    op.create_index("ix_phase4d_snapshots_customer", "phase4d_customer_snapshots", ["customer_user_id", "scope"])
    op.create_index("ix_phase4d_snapshots_expiry", "phase4d_customer_snapshots", ["expires_at"])

    op.create_table("phase4d_cache_outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("aggregate_kind", sa.String(16), nullable=False),
        sa.Column("aggregate_id", sa.String(80), nullable=False),
        sa.Column("customer_user_id", sa.Uuid(), sa.ForeignKey("customer_profiles.user_id")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("aggregate_kind IN ('ticket', 'order', 'payment', 'serial', 'warranty', 'repair', 'finance')", name="ck_phase4d_outbox_kind"),
    )
    op.create_index("ix_phase4d_outbox_customer", "phase4d_cache_outbox", ["customer_user_id"])
    op.create_index("ix_phase4d_outbox_occurred", "phase4d_cache_outbox", ["occurred_at"])

    op.create_table("phase4d_cache_consumers",
        sa.Column("consumer_name", sa.String(80), primary_key=True),
        sa.Column("last_event_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table("phase4d_cache_metrics",
        sa.Column("name", sa.String(80), primary_key=True),
        sa.Column("value", sa.BigInteger(), nullable=False, server_default="0"),
    )

    op.create_table("phase4d_ai_assists",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id")),
        sa.Column("customer_user_id", sa.Uuid(), sa.ForeignKey("customer_profiles.user_id")),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("model_provider", sa.String(80), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("draft", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("confirmed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("confirmation_note", sa.Text()),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('deterministic', 'provider')", name="ck_phase4d_ai_mode"),
        sa.CheckConstraint("status IN ('draft', 'confirmed', 'discarded', 'rejected', 'failed')", name="ck_phase4d_ai_status"),
    )
    op.create_index("ix_phase4d_ai_ticket", "phase4d_ai_assists", ["ticket_id"])

    op.create_table("phase4d_site_geolocations",
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("customer_sites.id"), primary_key=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(80), nullable=False, server_default="manual"),
        sa.Column("verified_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_phase4d_geo_lat"),
        sa.CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_phase4d_geo_lon"),
    )

    op.create_table("phase4d_forecast_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("customer_sites.id"), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("request_id", sa.String(80), nullable=False, unique=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("units", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_phase4d_forecast_site", "phase4d_forecast_snapshots", ["site_id", "fetched_at"])

    op.create_table("phase4d_weather_advisories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("customer_sites.id"), nullable=False),
        sa.Column("forecast_id", sa.Uuid(), sa.ForeignKey("phase4d_forecast_snapshots.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("window_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("acknowledged_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('heavy_rain', 'high_wind')", name="ck_phase4d_advisory_kind"),
        sa.CheckConstraint("status IN ('open', 'acknowledged', 'dismissed')", name="ck_phase4d_advisory_status"),
        sa.UniqueConstraint("forecast_id", "kind", name="uq_phase4d_advisory_forecast_kind"),
    )
    op.create_index("ix_phase4d_advisory_site", "phase4d_weather_advisories", ["site_id", "status"])

    op.create_table("phase4d_generation_readings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("device_ref", sa.String(80), nullable=False),
        sa.Column("event_id", sa.String(80), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("energy_wh", sa.Numeric(14, 2), nullable=False),
        sa.Column("power_w", sa.Numeric(12, 2)),
        sa.Column("unit", sa.String(16), nullable=False, server_default="Wh"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("rejection_reason", sa.String(240)),
        sa.Column("received_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('accepted', 'rejected', 'quarantined')", name="ck_phase4d_reading_status"),
        sa.UniqueConstraint("device_ref", "event_id", name="uq_phase4d_readings_device_event"),
    )
    op.create_index("ix_phase4d_readings_order", "phase4d_generation_readings", ["order_id", "measured_at"])


def downgrade():
    op.drop_table("phase4d_generation_readings")
    op.drop_table("phase4d_weather_advisories")
    op.drop_table("phase4d_forecast_snapshots")
    op.drop_table("phase4d_site_geolocations")
    op.drop_table("phase4d_ai_assists")
    op.drop_table("phase4d_cache_metrics")
    op.drop_table("phase4d_cache_consumers")
    op.drop_table("phase4d_cache_outbox")
    op.drop_table("phase4d_customer_snapshots")
