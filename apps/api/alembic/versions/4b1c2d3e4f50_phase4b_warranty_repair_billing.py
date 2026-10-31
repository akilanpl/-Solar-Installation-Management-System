"""Phase 4B warranty intelligence, approved repair estimates and billing.

Revision ID: 4b1c2d3e4f50
Revises: f4a7b2c1d093
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "4b1c2d3e4f50"
down_revision = "f4a7b2c1d093"
branch_labels = None
depends_on = None

SERIAL_STATUSES = ("in_stock", "reserved", "in_transit", "installed", "faulty", "returned", "quarantined")


def upgrade():
    op.execute("INSERT INTO warehouse_locations (code, name) VALUES ('QUARANTINE', 'Quarantine hold')")
    op.execute("ALTER TABLE equipment_serials DROP CONSTRAINT ck_equipment_serials_serial_status")
    op.create_check_constraint(
        op.f("ck_equipment_serials_serial_status"), "equipment_serials",
        sa.text("status IN ('in_stock', 'reserved', 'in_transit', 'installed', 'faulty', 'returned', 'quarantined')"),
    )

    op.create_table("warranty_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("issuer", sa.String(120), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table("warranty_policy_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("policy_id", sa.Uuid(), sa.ForeignKey("warranty_policies.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("applicable_components", postgresql.JSONB(), nullable=False),
        sa.Column("covered_fault_categories", postgresql.JSONB(), nullable=False),
        sa.Column("covered_components", postgresql.JSONB(), nullable=False),
        sa.Column("covered_repair_types", postgresql.JSONB(), nullable=False),
        sa.Column("exclusions", postgresql.JSONB(), nullable=False),
        sa.Column("labour_covered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("replacement_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("replacement_continuation", sa.String(16), nullable=False),
        sa.Column("replacement_warranty_days", sa.Integer(), nullable=True),
        sa.Column("manufacturer_auth_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("repeat_replacement_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("duration_days > 0", name="policy_version_duration"),
        sa.CheckConstraint("version_number >= 1", name="policy_version_number"),
        sa.UniqueConstraint("policy_id", "version_number", name="uq_policy_version"),
    )
    op.create_index("ix_policy_versions_policy", "warranty_policy_versions", ["policy_id"])
    op.create_table("serialized_asset_coverage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=False, unique=True),
        sa.Column("policy_version_id", sa.Uuid(), sa.ForeignKey("warranty_policy_versions.id"), nullable=False),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("customer_user_id", sa.Uuid(), sa.ForeignKey("customer_profiles.user_id"), nullable=False),
        sa.Column("site_id", sa.Uuid(), sa.ForeignKey("customer_sites.id"), nullable=True),
        sa.Column("delivery_id", sa.Uuid(), sa.ForeignKey("deliveries.id"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("replaced_by_serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=True),
        sa.Column("supersedes_coverage_id", sa.Uuid(), sa.ForeignKey("serialized_asset_coverage.id"), nullable=True),
        sa.Column("void_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active', 'expired', 'superseded', 'void')", name="asset_coverage_status"),
    )
    op.create_index("ix_asset_coverage_customer", "serialized_asset_coverage", ["customer_user_id"])
    op.create_table("coverage_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), sa.ForeignKey("warranty_policy_versions.id"), nullable=True),
        sa.Column("coverage_id", sa.Uuid(), sa.ForeignKey("serialized_asset_coverage.id"), nullable=True),
        sa.Column("policy_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("coverage_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("fault_category", sa.String(32), nullable=True),
        sa.Column("fault_code", sa.String(32), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("decided_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("verdict IN ('covered', 'not_covered', 'pending_verification', 'blocked')", name="coverage_decision_verdict"),
        sa.UniqueConstraint("ticket_id", "idempotency_key", name="uq_coverage_decision_idem"),
    )
    op.create_index("ix_coverage_decisions_ticket", "coverage_decisions", ["ticket_id"])
    op.create_table("warranty_exceptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_ref", sa.String(200), nullable=True),
        sa.Column("decided_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("decision IN ('covered', 'not_covered')", name="warranty_exception_decision"),
        sa.UniqueConstraint("ticket_id", "serial_id", name="uq_warranty_exception"),
    )
    op.create_index("ix_warranty_exceptions_ticket", "warranty_exceptions", ["ticket_id"])
    op.create_table("service_price_books",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("labour_rates", postgresql.JSONB(), nullable=False),
        sa.Column("part_prices", postgresql.JSONB(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("version", name="uq_price_book_version"),
    )
    op.create_table("service_tax_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("rate_bps", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("rate_bps >= 0", name="tax_policy_rate"),
        sa.UniqueConstraint("version", name="uq_tax_policy_version"),
    )
    op.create_table("service_estimates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("repair_job_id", sa.Uuid(), sa.ForeignKey("ticket_repair_jobs.id"), nullable=False),
        sa.Column("coverage_decision_id", sa.Uuid(), sa.ForeignKey("coverage_decisions.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("lines", postgresql.JSONB(), nullable=False),
        sa.Column("parts_minor", sa.Integer(), nullable=False),
        sa.Column("labour_minor", sa.Integer(), nullable=False),
        sa.Column("tax_minor", sa.Integer(), nullable=False),
        sa.Column("covered_minor", sa.Integer(), nullable=False),
        sa.Column("customer_payable_minor", sa.Integer(), nullable=False),
        sa.Column("price_book_version", sa.Integer(), nullable=False),
        sa.Column("tax_policy_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('proposed', 'accepted', 'rejected', 'superseded', 'expired')", name="service_estimate_status"),
        sa.UniqueConstraint("ticket_id", "version", name="uq_estimate_version"),
        sa.UniqueConstraint("ticket_id", "idempotency_key", name="uq_estimate_idem"),
    )
    op.create_index("ix_service_estimates_ticket", "service_estimates", ["ticket_id"])
    op.create_table("estimate_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("estimate_id", sa.Uuid(), sa.ForeignKey("service_estimates.id"), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("estimate_version", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("customer_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("decision IN ('accepted', 'rejected')", name="estimate_decision_value"),
        sa.UniqueConstraint("estimate_id", name="uq_estimate_decision"),
    )
    op.create_index("ix_estimate_decisions_ticket", "estimate_decisions", ["ticket_id"])
    op.create_table("service_invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("estimate_id", sa.Uuid(), sa.ForeignKey("service_estimates.id"), nullable=False),
        sa.Column("estimate_version", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("lines", postgresql.JSONB(), nullable=False),
        sa.Column("parts_minor", sa.Integer(), nullable=False),
        sa.Column("labour_minor", sa.Integer(), nullable=False),
        sa.Column("tax_minor", sa.Integer(), nullable=False),
        sa.Column("covered_minor", sa.Integer(), nullable=False),
        sa.Column("customer_payable_minor", sa.Integer(), nullable=False),
        sa.Column("credited_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumption_operation_id", sa.Uuid(), sa.ForeignKey("stock_operations.id"), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('outstanding', 'pending_payment', 'credited')", name="service_invoice_status"),
        sa.UniqueConstraint("estimate_id", "estimate_version", name="uq_invoice_estimate"),
    )
    op.create_index("ix_service_invoices_ticket", "service_invoices", ["ticket_id"])
    op.create_table("service_credit_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("invoice_id", sa.Uuid(), sa.ForeignKey("service_invoices.id"), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_minor > 0", name="credit_note_amount"),
    )
    op.create_index("ix_credit_notes_invoice", "service_credit_notes", ["invoice_id"])
    op.create_table("replacement_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("reference", sa.String(20), nullable=False, unique=True),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("service_tickets.id"), nullable=False),
        sa.Column("coverage_decision_id", sa.Uuid(), sa.ForeignKey("coverage_decisions.id"), nullable=False),
        sa.Column("old_serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=False),
        sa.Column("new_serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=False, unique=True),
        sa.Column("issue_operation_id", sa.Uuid(), sa.ForeignKey("stock_operations.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("manufacturer_status", sa.String(16), nullable=False),
        sa.Column("manufacturer_evidence_ref", sa.String(200), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('proposed', 'approved', 'pending_manufacturer', 'issued', 'installed', 'cancelled')", name="replacement_status"),
        sa.CheckConstraint("manufacturer_status IN ('not_required', 'pending', 'approved')", name="replacement_manufacturer"),
        sa.UniqueConstraint("ticket_id", "idempotency_key", name="uq_replacement_idem"),
    )
    op.create_index("ix_replacements_ticket", "replacement_decisions", ["ticket_id"])
    op.create_table("return_inspections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("replacement_id", sa.Uuid(), sa.ForeignKey("replacement_decisions.id"), nullable=False),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=False),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("restock_operation_id", sa.Uuid(), sa.ForeignKey("stock_operations.id"), nullable=True),
        sa.Column("inspected_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("verdict IN ('quarantined', 'restocked', 'scrapped')", name="return_inspection_verdict"),
        sa.UniqueConstraint("replacement_id", name="uq_return_inspection"),
    )


def downgrade():
    op.execute("DELETE FROM warehouse_locations WHERE code = 'QUARANTINE'")
    op.drop_table("return_inspections")
    op.drop_index("ix_replacements_ticket", table_name="replacement_decisions")
    op.drop_table("replacement_decisions")
    op.drop_index("ix_credit_notes_invoice", table_name="service_credit_notes")
    op.drop_table("service_credit_notes")
    op.drop_index("ix_service_invoices_ticket", table_name="service_invoices")
    op.drop_table("service_invoices")
    op.drop_index("ix_estimate_decisions_ticket", table_name="estimate_decisions")
    op.drop_table("estimate_decisions")
    op.drop_index("ix_service_estimates_ticket", table_name="service_estimates")
    op.drop_table("service_estimates")
    op.drop_table("service_tax_policies")
    op.drop_table("service_price_books")
    op.drop_index("ix_warranty_exceptions_ticket", table_name="warranty_exceptions")
    op.drop_table("warranty_exceptions")
    op.drop_index("ix_coverage_decisions_ticket", table_name="coverage_decisions")
    op.drop_table("coverage_decisions")
    op.drop_index("ix_asset_coverage_customer", table_name="serialized_asset_coverage")
    op.drop_table("serialized_asset_coverage")
    op.drop_index("ix_policy_versions_policy", table_name="warranty_policy_versions")
    op.drop_table("warranty_policy_versions")
    op.drop_table("warranty_policies")
    op.execute("ALTER TABLE equipment_serials DROP CONSTRAINT ck_equipment_serials_serial_status")
    op.create_check_constraint(
        "serial_status", "equipment_serials",
        sa.text("status IN ('in_stock', 'reserved', 'in_transit', 'installed', 'faulty')"),
    )
