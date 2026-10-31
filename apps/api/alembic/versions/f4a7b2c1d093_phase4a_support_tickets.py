"""Phase 4A support tickets through to confirmed resolution.

Revision ID: f4a7b2c1d093
Revises: e6a2b3c4d5f6
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f4a7b2c1d093"
down_revision = "e6a2b3c4d5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("service_tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("customer_user_id", sa.Uuid(), sa.ForeignKey("customer_profiles.user_id"), nullable=False),
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("customer_sites.id"), nullable=True),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=True),
        sa.Column("fault_code", sa.String(32), nullable=True),
        sa.Column("symptoms", sa.Text(), nullable=False),
        sa.Column("customer_urgency", sa.String(16), nullable=False),
        sa.Column("contact_preference", sa.String(16), nullable=False),
        sa.Column("category", sa.String(16), nullable=True),
        sa.Column("verified_priority", sa.String(16), nullable=True),
        sa.Column("assigned_support_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resolution_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolution_summary", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('open', 'triaged', 'assigned', 'in_progress', 'waiting_customer', 'resolved', 'customer_confirmed', 'closed', 'cancelled')", name="service_ticket_status"),
        sa.CheckConstraint("customer_urgency IN ('low', 'normal', 'high', 'urgent')", name="service_ticket_urgency"),
        sa.CheckConstraint("contact_preference IN ('email', 'phone', 'either')", name="service_ticket_contact"),
        sa.CheckConstraint("verified_priority IS NULL OR verified_priority IN ('low', 'normal', 'high', 'critical')", name="service_ticket_verified_priority"),
        sa.CheckConstraint("category IS NULL OR category IN ('inverter', 'panel', 'battery', 'mounting', 'wiring', 'monitoring', 'other')", name="service_ticket_category"),
        sa.CheckConstraint("resolution_version >= 0", name="service_ticket_resolution_version"),
        sa.UniqueConstraint("customer_user_id", "idempotency_key", name="uq_service_tickets_idempotency"),
    )
    op.create_index("ix_service_tickets_customer_status", "service_tickets", ["customer_user_id", "status"])
    op.create_index("ix_service_tickets_order", "service_tickets", ["order_id"])

    op.create_table("service_ticket_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_service_ticket_events_ticket", "service_ticket_events", ["ticket_id"])

    op.create_table("ticket_repair_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=True),
        sa.Column("technician_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("scheduled_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrival_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("diagnostics", postgresql.JSONB(), nullable=True),
        sa.Column("work_performed", sa.Text(), nullable=True),
        sa.Column("parts_used", postgresql.JSONB(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('assigned', 'in_progress', 'work_submitted', 'cancelled')", name="repair_job_status"),
        sa.UniqueConstraint("ticket_id", "idempotency_key", name="uq_repair_jobs_idempotency"),
    )
    op.create_index("ix_ticket_repair_jobs_ticket_id", "ticket_repair_jobs", ["ticket_id"])
    op.create_index("ix_repair_jobs_technician_status", "ticket_repair_jobs", ["technician_user_id", "status"])

    op.create_table("service_ticket_attachments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("repair_job_id", sa.Uuid(), sa.ForeignKey("ticket_repair_jobs.id"), nullable=True),
        sa.Column("storage_key", sa.String(32), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("size_bytes > 0 AND size_bytes <= 5000000", name="ticket_attachment_size"),
    )
    op.create_index("ix_service_ticket_attachments_ticket_id", "service_ticket_attachments", ["ticket_id"])

    op.create_table("resolution_acknowledgments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("repair_job_id", sa.Uuid(), sa.ForeignKey("ticket_repair_jobs.id"), nullable=False),
        sa.Column("summary_version", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("customer_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("decision IN ('confirmed', 'disputed')", name="acknowledgment_decision"),
        sa.UniqueConstraint("ticket_id", "summary_version", name="uq_acknowledgment_version"),
    )
    op.create_index("ix_resolution_acknowledgments_ticket_id", "resolution_acknowledgments", ["ticket_id"])


def downgrade():
    op.drop_index("ix_resolution_acknowledgments_ticket_id", table_name="resolution_acknowledgments")
    op.drop_table("resolution_acknowledgments")
    op.drop_index("ix_service_ticket_attachments_ticket_id", table_name="service_ticket_attachments")
    op.drop_table("service_ticket_attachments")
    op.drop_index("ix_repair_jobs_technician_status", table_name="ticket_repair_jobs")
    op.drop_index("ix_ticket_repair_jobs_ticket_id", table_name="ticket_repair_jobs")
    op.drop_table("ticket_repair_jobs")
    op.drop_index("ix_service_ticket_events_ticket", table_name="service_ticket_events")
    op.drop_table("service_ticket_events")
    op.drop_index("ix_service_tickets_order", table_name="service_tickets")
    op.drop_index("ix_service_tickets_customer_status", table_name="service_tickets")
    op.drop_table("service_tickets")
