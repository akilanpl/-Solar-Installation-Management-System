"""Share production abuse limits across workers and restarts."""

from alembic import op
import sqlalchemy as sa

revision = "e2a8b9c0d1f2"
down_revision = "d1f7a8b9c0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rate_limit_buckets",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("hits > 0", name=op.f("ck_rate_limit_buckets_hits_positive")),
    )
    op.create_index("ix_rate_limit_buckets_expires_at", "rate_limit_buckets", ["expires_at"])


def downgrade():
    op.drop_table("rate_limit_buckets")
