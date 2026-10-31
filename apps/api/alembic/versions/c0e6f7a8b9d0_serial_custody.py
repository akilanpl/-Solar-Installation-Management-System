"""Distinguish unverified registration, delivered custody and installation."""

from alembic import op
import sqlalchemy as sa

revision = "c0e6f7a8b9d0"
down_revision = "b9d5e6f7a8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "equipment_serials",
        sa.Column("delivery_line_id", sa.Uuid(), sa.ForeignKey("delivery_lines.id")),
    )
    op.drop_constraint(
        op.f("ck_equipment_serials_serial_status"), "equipment_serials", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_equipment_serials_serial_status"),
        "equipment_serials",
        "status IN ('registered','in_stock','reserved','in_transit','delivered','installed','faulty')",
    )
    # Historical custody is not invented or rewritten. Legacy unlinked units
    # remain readable but assignment now requires validated receipt provenance.


def downgrade():
    if op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM equipment_serials WHERE delivery_line_id IS NOT NULL OR status IN ('registered','delivered')"
        )
    ):
        raise RuntimeError(
            "Refusing to discard serial custody; restore a verified isolated backup."
        )
    op.drop_constraint(
        op.f("ck_equipment_serials_serial_status"), "equipment_serials", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_equipment_serials_serial_status"),
        "equipment_serials",
        "status IN ('in_stock','reserved','in_transit','installed','faulty')",
    )
    op.drop_column("equipment_serials", "delivery_line_id")
