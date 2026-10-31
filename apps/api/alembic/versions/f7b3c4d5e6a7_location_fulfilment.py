"""Location allocations, partial deliveries, inspected returns, supplier records.

Existing ledger and delivery quantities are preserved. Existing lines came from
MAIN; their source is explicitly backfilled. Demand reservations are not falsely
backfilled as physical allocations. Downgrade refuses data it cannot preserve.
"""

from alembic import op
import sqlalchemy as sa

revision = "f7b3c4d5e6a7"
down_revision = "e6a2b3c4d5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("uq_deliveries_order_id", "deliveries", type_="unique")
    op.add_column(
        "delivery_lines",
        sa.Column(
            "location_code",
            sa.String(32),
            sa.ForeignKey("warehouse_locations.code"),
            nullable=False,
            server_default="MAIN",
        ),
    )
    op.create_check_constraint(
        op.f("ck_delivery_lines_quantity_positive"), "delivery_lines", "quantity > 0"
    )
    op.create_table(
        "stock_allocations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "reservation_id", sa.Uuid(), sa.ForeignKey("stock_reservations.id"), nullable=False
        ),
        sa.Column(
            "location_code",
            sa.String(32),
            sa.ForeignKey("warehouse_locations.code"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("picked_quantity", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "reservation_id", "location_code", name="uq_allocation_reservation_location"
        ),
        sa.CheckConstraint(
            "quantity > 0 AND picked_quantity >= 0 AND picked_quantity <= quantity",
            name=op.f("ck_stock_allocations_quantities"),
        ),
    )
    op.create_index("ix_stock_allocations_reservation_id", "stock_allocations", ["reservation_id"])
    op.create_table(
        "goods_returns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "delivery_line_id", sa.Uuid(), sa.ForeignKey("delivery_lines.id"), nullable=False
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("inspection_note", sa.Text()),
        sa.Column("disposition", sa.String(16)),
        sa.Column("operation_id", sa.Uuid(), sa.ForeignKey("stock_operations.id")),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id")),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("inspected_by_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("inspected_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('authorized','inspected')", name=op.f("ck_goods_returns_status")
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_goods_returns_quantity")),
        sa.UniqueConstraint("created_by_user_id", "idempotency_key", name="uq_return_idempotency"),
    )
    op.create_index("ix_goods_returns_delivery_line_id", "goods_returns", ["delivery_line_id"])
    op.create_table(
        "supplier_orders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "replenishment_request_id",
            sa.Uuid(),
            sa.ForeignKey("replenishment_requests.id"),
            nullable=False,
        ),
        sa.Column("supplier_name", sa.String(160), nullable=False),
        sa.Column("supplier_reference", sa.String(160), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("received_operation_id", sa.Uuid(), sa.ForeignKey("stock_operations.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('draft','ordered','received','cancelled')",
            name=op.f("ck_supplier_orders_status"),
        ),
        sa.UniqueConstraint("replenishment_request_id", name="uq_supplier_order_replenishment"),
    )
    op.execute(
        "INSERT INTO warehouse_locations (code,name) VALUES ('QUARANTINE','Inspected damaged goods - unavailable for allocation') ON CONFLICT DO NOTHING"
    )


def downgrade():
    bind = op.get_bind()
    if (
        bind.scalar(
            sa.text(
                "SELECT count(*) FROM (SELECT order_id FROM deliveries GROUP BY order_id HAVING count(*) > 1) x"
            )
        )
        or bind.scalar(sa.text("SELECT count(*) FROM goods_returns"))
        or bind.scalar(sa.text("SELECT count(*) FROM supplier_orders"))
        or bind.scalar(sa.text("SELECT count(*) FROM stock_allocations"))
    ):
        raise RuntimeError(
            "Refusing lossy operational downgrade. Restore a verified backup on isolated infrastructure."
        )
    op.drop_table("supplier_orders")
    op.drop_table("goods_returns")
    op.drop_table("stock_allocations")
    op.drop_constraint(op.f("ck_delivery_lines_quantity_positive"), "delivery_lines", type_="check")
    op.drop_column("delivery_lines", "location_code")
    op.create_unique_constraint("uq_deliveries_order_id", "deliveries", ["order_id"])
