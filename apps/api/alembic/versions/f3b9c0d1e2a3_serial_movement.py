"""Declare hardware serial policy and retain per-operation unit movements.

The current catalogue defines panels, inverters, battery and MPPT controller as
serialized hardware. No unit identity or historical movement is fabricated.
Existing unidentified balances require actual serial registration before picking.
"""

from alembic import op
import sqlalchemy as sa

revision = "f3b9c0d1e2a3"
down_revision = "e2a8b9c0d1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "catalogue_components",
        sa.Column(
            "requires_serial_tracking", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.execute(
        "UPDATE catalogue_components SET requires_serial_tracking=true WHERE code IN ('PANEL-550','INV-ONG','INV-OFG','BAT-1KWH','CC-MPPT')"
    )
    op.create_table(
        "stock_serial_movements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("operation_id", sa.Uuid(), sa.ForeignKey("stock_operations.id"), nullable=False),
        sa.Column("line_id", sa.Uuid(), sa.ForeignKey("stock_operation_lines.id"), nullable=False),
        sa.Column("delivery_line_id", sa.Uuid(), sa.ForeignKey("delivery_lines.id")),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=False),
        sa.Column("serial_number", sa.String(64), nullable=False),
        sa.UniqueConstraint("operation_id", "serial_id", name="uq_operation_serial"),
    )
    op.create_index(
        "ix_stock_serial_movements_operation_id", "stock_serial_movements", ["operation_id"]
    )
    op.create_index("ix_stock_serial_movements_line_id", "stock_serial_movements", ["line_id"])
    op.create_index(
        "ix_stock_serial_movements_delivery_line_id", "stock_serial_movements", ["delivery_line_id"]
    )
    op.drop_constraint(
        op.f("ck_equipment_serials_serial_status"), "equipment_serials", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_equipment_serials_serial_status"),
        "equipment_serials",
        "status IN ('registered', 'in_stock', 'reserved', 'in_transit', 'delivered', 'installed', 'faulty', 'missing', 'returned', 'quarantined')",
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text("SELECT count(*) FROM stock_serial_movements")
    ) or op.get_bind().scalar(
        sa.text("SELECT count(*) FROM equipment_serials WHERE status='missing'")
    ):
        raise RuntimeError("Refusing to discard serial movements or missing-unit history.")
    op.drop_table("stock_serial_movements")
    op.drop_column("catalogue_components", "requires_serial_tracking")
    op.drop_constraint(
        op.f("ck_equipment_serials_serial_status"), "equipment_serials", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_equipment_serials_serial_status"),
        "equipment_serials",
        "status IN ('registered','in_stock','reserved','in_transit','delivered','installed','faulty')",
    )
