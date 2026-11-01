"""phase 3 warehouse installation warranty

Revision ID: d5f1a2b3c4e5
Revises: c4e8a1b27d90
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5f1a2b3c4e5"
down_revision: Union[str, Sequence[str], None] = "c4e8a1b27d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "warehouse_locations",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_warehouse_locations")),
    )
    op.execute(
        "INSERT INTO warehouse_locations (code, name) VALUES "
        "('MAIN', 'Main warehouse'), "
        "('SITE', 'Site staging')"
    )
    op.create_table(
        "stock_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=20), nullable=False),
        sa.Column("operation_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_order_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("operation_type IN ('receipt', 'transfer', 'delivery', 'adjustment')", name=op.f("ck_stock_operations_operation_type")),
        sa.CheckConstraint("status IN ('draft', 'ready', 'done', 'cancelled')", name=op.f("ck_stock_operations_operation_status")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name=op.f("fk_stock_operations_created_by_user_id_users")),
        sa.ForeignKeyConstraint(["source_order_id"], ["sales_orders.id"], name=op.f("fk_stock_operations_source_order_id_sales_orders")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_operations")),
        sa.UniqueConstraint("created_by_user_id", "idempotency_key", name="uq_stock_operations_idem"),
        sa.UniqueConstraint("reference", name=op.f("uq_stock_operations_reference")),
    )
    op.create_table(
        "stock_operation_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("component_code", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("from_location", sa.String(length=32), nullable=True),
        sa.Column("to_location", sa.String(length=32), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity <> 0", name=op.f("ck_stock_operation_lines_quantity_nonzero")),
        sa.ForeignKeyConstraint(["component_code"], ["catalogue_components.code"], name=op.f("fk_stock_operation_lines_component_code_catalogue_components")),
        sa.ForeignKeyConstraint(["from_location"], ["warehouse_locations.code"], name=op.f("fk_stock_operation_lines_from_location_warehouse_locations")),
        sa.ForeignKeyConstraint(["operation_id"], ["stock_operations.id"], name=op.f("fk_stock_operation_lines_operation_id_stock_operations")),
        sa.ForeignKeyConstraint(["to_location"], ["warehouse_locations.code"], name=op.f("fk_stock_operation_lines_to_location_warehouse_locations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_operation_lines")),
    )
    op.create_index(op.f("ix_stock_operation_lines_operation_id"), "stock_operation_lines", ["operation_id"], unique=False)
    op.create_table(
        "stock_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("component_code", sa.String(length=32), nullable=False),
        sa.Column("location_code", sa.String(length=32), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["component_code"], ["catalogue_components.code"], name=op.f("fk_stock_ledger_component_code_catalogue_components")),
        sa.ForeignKeyConstraint(["location_code"], ["warehouse_locations.code"], name=op.f("fk_stock_ledger_location_code_warehouse_locations")),
        sa.ForeignKeyConstraint(["operation_id"], ["stock_operations.id"], name=op.f("fk_stock_ledger_operation_id_stock_operations")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_ledger")),
    )
    op.create_index(op.f("ix_stock_ledger_operation_id"), "stock_ledger", ["operation_id"], unique=False)
    op.create_index(op.f("ix_stock_ledger_component_code"), "stock_ledger", ["component_code"], unique=False)
    op.create_index(op.f("ix_stock_ledger_location_code"), "stock_ledger", ["location_code"], unique=False)
    op.create_table(
        "stock_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("component_code", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('reserved', 'consumed', 'released')", name=op.f("ck_stock_reservations_reservation_status")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_stock_reservations_reservation_quantity")),
        sa.ForeignKeyConstraint(["component_code"], ["catalogue_components.code"], name=op.f("fk_stock_reservations_component_code_catalogue_components")),
        sa.ForeignKeyConstraint(["order_id"], ["sales_orders.id"], name=op.f("fk_stock_reservations_order_id_sales_orders")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_reservations")),
        sa.UniqueConstraint("order_id", "component_code", name="uq_reservation_order_component"),
    )
    op.create_index(op.f("ix_stock_reservations_order_id"), "stock_reservations", ["order_id"], unique=False)
    op.create_table(
        "equipment_serials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("serial_number", sa.String(length=64), nullable=False),
        sa.Column("component_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("location_code", sa.String(length=32), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("operation_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('in_stock', 'reserved', 'in_transit', 'installed', 'faulty')", name=op.f("ck_equipment_serials_serial_status")),
        sa.ForeignKeyConstraint(["component_code"], ["catalogue_components.code"], name=op.f("fk_equipment_serials_component_code_catalogue_components")),
        sa.ForeignKeyConstraint(["location_code"], ["warehouse_locations.code"], name=op.f("fk_equipment_serials_location_code_warehouse_locations")),
        sa.ForeignKeyConstraint(["operation_id"], ["stock_operations.id"], name=op.f("fk_equipment_serials_operation_id_stock_operations")),
        sa.ForeignKeyConstraint(["order_id"], ["sales_orders.id"], name=op.f("fk_equipment_serials_order_id_sales_orders")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_equipment_serials")),
        sa.UniqueConstraint("serial_number", name=op.f("uq_equipment_serials_serial_number")),
    )
    op.create_index(op.f("ix_equipment_serials_component_code"), "equipment_serials", ["component_code"], unique=False)
    op.create_table(
        "deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=20), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('prepared', 'in_transit', 'delivered', 'confirmed', 'cancelled')", name=op.f("ck_deliveries_delivery_status")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name=op.f("fk_deliveries_created_by_user_id_users")),
        sa.ForeignKeyConstraint(["order_id"], ["sales_orders.id"], name=op.f("fk_deliveries_order_id_sales_orders")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deliveries")),
        sa.UniqueConstraint("created_by_user_id", "idempotency_key", name="uq_deliveries_idem"),
        sa.UniqueConstraint("order_id", name=op.f("uq_deliveries_order_id")),
        sa.UniqueConstraint("reference", name=op.f("uq_deliveries_reference")),
    )
    op.create_table(
        "delivery_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delivery_id", sa.Uuid(), nullable=False),
        sa.Column("component_code", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["component_code"], ["catalogue_components.code"], name=op.f("fk_delivery_lines_component_code_catalogue_components")),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], name=op.f("fk_delivery_lines_delivery_id_deliveries")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_delivery_lines")),
    )
    op.create_index(op.f("ix_delivery_lines_delivery_id"), "delivery_lines", ["delivery_id"], unique=False)
    op.create_table(
        "replenishment_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=20), nullable=False),
        sa.Column("component_code", sa.String(length=32), nullable=False),
        sa.Column("location_code", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('proposed', 'approved', 'rejected', 'ordered', 'received', 'cancelled')", name=op.f("ck_replenishment_requests_replenishment_status")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_replenishment_requests_replenishment_quantity")),
        sa.ForeignKeyConstraint(["component_code"], ["catalogue_components.code"], name=op.f("fk_replenishment_requests_component_code_catalogue_components")),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], name=op.f("fk_replenishment_requests_decided_by_user_id_users")),
        sa.ForeignKeyConstraint(["location_code"], ["warehouse_locations.code"], name=op.f("fk_replenishment_requests_location_code_warehouse_locations")),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], name=op.f("fk_replenishment_requests_requested_by_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_replenishment_requests")),
        sa.UniqueConstraint("reference", name=op.f("uq_replenishment_requests_reference")),
    )
    op.create_table(
        "installation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=20), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("scheduling_request_id", sa.Uuid(), nullable=False),
        sa.Column("technician_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("slot_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrival_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_verified", sa.Boolean(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("signature", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('created', 'scheduled', 'en_route', 'on_site', 'completed', 'cancelled')", name=op.f("ck_installation_jobs_job_status")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name=op.f("fk_installation_jobs_created_by_user_id_users")),
        sa.ForeignKeyConstraint(["order_id"], ["sales_orders.id"], name=op.f("fk_installation_jobs_order_id_sales_orders")),
        sa.ForeignKeyConstraint(["scheduling_request_id"], ["installation_scheduling_requests.id"], name=op.f("fk_installation_jobs_scheduling_request_id_installation_scheduling_requests")),
        sa.ForeignKeyConstraint(["technician_user_id"], ["users.id"], name=op.f("fk_installation_jobs_technician_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_installation_jobs")),
        sa.UniqueConstraint("order_id", name=op.f("uq_installation_jobs_order_id")),
        sa.UniqueConstraint("reference", name=op.f("uq_installation_jobs_reference")),
    )
    op.create_table(
        "installation_otps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("purpose IN ('job_customer_verify')", name=op.f("ck_installation_otps_otp_purpose")),
        sa.ForeignKeyConstraint(["job_id"], ["installation_jobs.id"], name=op.f("fk_installation_otps_job_id_installation_jobs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_installation_otps")),
    )
    op.create_index(op.f("ix_installation_otps_job_id"), "installation_otps", ["job_id"], unique=False)
    op.create_index(
        "ix_installation_otps_job_open", "installation_otps", ["job_id"], unique=False, postgresql_where=sa.text("consumed_at IS NULL")
    )
    op.create_table(
        "warranties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("customer_user_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("coverage_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active', 'expired', 'void')", name=op.f("ck_warranties_warranty_status")),
        sa.ForeignKeyConstraint(["customer_user_id"], ["users.id"], name=op.f("fk_warranties_customer_user_id_users")),
        sa.ForeignKeyConstraint(["order_id"], ["sales_orders.id"], name=op.f("fk_warranties_order_id_sales_orders")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_warranties")),
        sa.UniqueConstraint("order_id", name=op.f("uq_warranties_order_id")),
    )
    op.drop_constraint(op.f("ck_installation_scheduling_requests_status"), "installation_scheduling_requests", type_="check")
    op.create_check_constraint(
        op.f("ck_installation_scheduling_requests_status"),
        "installation_scheduling_requests",
        "status IN ('unscheduled', 'scheduled', 'assigned', 'completed', 'cancelled')",
    )
    op.drop_constraint(op.f("ck_warehouse_preparation_requests_status"), "warehouse_preparation_requests", type_="check")
    op.create_check_constraint(
        op.f("ck_warehouse_preparation_requests_status"),
        "warehouse_preparation_requests",
        "status IN ('pending_preparation', 'picking', 'ready', 'delivered')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_warehouse_preparation_requests_status"), "warehouse_preparation_requests", type_="check")
    op.create_check_constraint(
        op.f("ck_warehouse_preparation_requests_status"),
        "warehouse_preparation_requests",
        "status IN ('pending_preparation')",
    )
    op.drop_constraint(op.f("ck_installation_scheduling_requests_status"), "installation_scheduling_requests", type_="check")
    op.create_check_constraint(
        op.f("ck_installation_scheduling_requests_status"),
        "installation_scheduling_requests",
        "status IN ('unscheduled')",
    )
    op.drop_table("warranties")
    op.drop_index("ix_installation_otps_job_open", table_name="installation_otps")
    op.drop_index(op.f("ix_installation_otps_job_id"), table_name="installation_otps")
    op.drop_table("installation_otps")
    op.drop_table("installation_jobs")
    op.drop_table("replenishment_requests")
    op.drop_index(op.f("ix_delivery_lines_delivery_id"), table_name="delivery_lines")
    op.drop_table("delivery_lines")
    op.drop_table("deliveries")
    op.drop_index(op.f("ix_equipment_serials_component_code"), table_name="equipment_serials")
    op.drop_table("equipment_serials")
    op.drop_index(op.f("ix_stock_reservations_order_id"), table_name="stock_reservations")
    op.drop_table("stock_reservations")
    op.drop_index(op.f("ix_stock_ledger_location_code"), table_name="stock_ledger")
    op.drop_index(op.f("ix_stock_ledger_component_code"), table_name="stock_ledger")
    op.drop_index(op.f("ix_stock_ledger_operation_id"), table_name="stock_ledger")
    op.drop_table("stock_ledger")
    op.drop_index(op.f("ix_stock_operation_lines_operation_id"), table_name="stock_operation_lines")
    op.drop_table("stock_operation_lines")
    op.drop_table("stock_operations")
    op.drop_table("warehouse_locations")
