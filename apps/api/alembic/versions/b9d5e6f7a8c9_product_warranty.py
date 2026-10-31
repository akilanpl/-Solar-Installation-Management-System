"""Immutable product policy versions, order snapshots and unit coverage."""

from alembic import op
import sqlalchemy as sa

revision = "b9d5e6f7a8c9"
down_revision = "a8c4d5e6f7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_warranty_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "component_code",
            sa.String(32),
            sa.ForeignKey("catalogue_components.code"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("months", sa.Integer(), nullable=False),
        sa.Column("activation_event", sa.String(16), nullable=False),
        sa.Column("terms", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("component_code", "version", name="uq_product_warranty_version"),
        sa.CheckConstraint(
            "months > 0 AND months <= 600", name=op.f("ck_product_warranty_policies_duration")
        ),
        sa.CheckConstraint(
            "activation_event IN ('delivery','installation')",
            name=op.f("ck_product_warranty_policies_activation"),
        ),
    )
    op.create_table(
        "order_warranty_terms",
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("sales_orders.id"), primary_key=True),
        sa.Column(
            "component_code",
            sa.String(32),
            sa.ForeignKey("catalogue_components.code"),
            primary_key=True,
        ),
        sa.Column(
            "policy_id", sa.Uuid(), sa.ForeignKey("product_warranty_policies.id"), nullable=False
        ),
    )
    op.create_table(
        "serial_warranties",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("serial_id", sa.Uuid(), sa.ForeignKey("equipment_serials.id"), nullable=False),
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column(
            "policy_id", sa.Uuid(), sa.ForeignKey("product_warranty_policies.id"), nullable=False
        ),
        sa.Column("delivery_id", sa.Uuid(), sa.ForeignKey("deliveries.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("void_reason", sa.Text()),
        sa.UniqueConstraint("serial_id", "order_id", name="uq_serial_order_warranty"),
        sa.CheckConstraint("status IN ('active','void')", name=op.f("ck_serial_warranties_status")),
    )


def downgrade():
    for table in ["serial_warranties", "order_warranty_terms", "product_warranty_policies"]:
        if op.get_bind().scalar(sa.text("SELECT count(*) FROM " + table)):
            raise RuntimeError(
                "Refusing to discard policy/coverage history; restore a verified isolated backup."
            )
    op.drop_table("serial_warranties")
    op.drop_table("order_warranty_terms")
    op.drop_table("product_warranty_policies")
