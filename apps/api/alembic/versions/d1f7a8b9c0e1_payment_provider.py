"""Provider order/event custody. Only test credentials are enabled by the adapter."""

from alembic import op
import sqlalchemy as sa

revision = "d1f7a8b9c0e1"
down_revision = "c0e6f7a8b9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(op.f("ck_payment_intents_method"), "payment_intents", type_="check")
    op.create_check_constraint(
        op.f("ck_payment_intents_method"),
        "payment_intents",
        "method IN ('sandbox','cash','razorpay')",
    )
    op.create_table(
        "provider_payment_orders",
        sa.Column("intent_id", sa.Uuid(), sa.ForeignKey("payment_intents.id"), primary_key=True),
        sa.Column("provider_order_id", sa.String(80), unique=True),
        sa.Column("provider_payment_id", sa.String(80), unique=True),
        sa.Column("refunded_minor", sa.Integer(), nullable=False),
        sa.Column("unapplied_minor", sa.Integer(), nullable=False),
        sa.Column("reconciled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "refunded_minor >= 0 AND unapplied_minor >= 0",
            name=op.f("ck_provider_payment_orders_amounts"),
        ),
    )
    op.create_table(
        "provider_events",
        sa.Column("event_id", sa.String(200), primary_key=True),
        sa.Column("body_hash", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("intent_id", sa.Uuid(), sa.ForeignKey("payment_intents.id")),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade():
    if op.get_bind().scalar(
        sa.text("SELECT count(*) FROM provider_payment_orders")
    ) or op.get_bind().scalar(sa.text("SELECT count(*) FROM provider_events")):
        raise RuntimeError("Refusing to discard payment/provider evidence.")
    op.drop_table("provider_events")
    op.drop_table("provider_payment_orders")
    op.drop_constraint(op.f("ck_payment_intents_method"), "payment_intents", type_="check")
    op.create_check_constraint(
        op.f("ck_payment_intents_method"), "payment_intents", "method IN ('sandbox','cash')"
    )
