"""Merge completed integration and Phase 4 migrations without changing source rows.

The earlier sibling CHECK replacements each recognized only their own serial
states. Upgrade definitions are widened to their union so an already populated
sibling can reach this merge. This revision also corrects constraints on databases
where those earlier revisions were already applied. No status is translated.
"""

from alembic import op

revision = "6a1b2c3d4e50"
down_revision = ("f3b9c0d1e2a3", "4c1c2d3e4f50", "4d1a2b3c4d50", "35958a00676d")
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(op.f("ck_equipment_serials_serial_status"), "equipment_serials", type_="check")
    op.create_check_constraint(
        op.f("ck_equipment_serials_serial_status"),
        "equipment_serials",
        "status IN ('registered', 'in_stock', 'reserved', 'in_transit', 'delivered', 'installed', 'faulty', 'missing', 'returned', 'quarantined')",
    )


def downgrade():
    # The union remains valid on each sibling. Narrowing it would discard or
    # invalidate legitimate custody states; branch downgrades enforce their own
    # preservation guards. Removing only this merge has no schema rollback.
    pass
