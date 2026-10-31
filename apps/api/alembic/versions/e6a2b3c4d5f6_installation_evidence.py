"""Persist installation upload custody and file hashes.

Revision ID: e6a2b3c4d5f6
Revises: d5f1a2b3c4e5
"""
from alembic import op
import sqlalchemy as sa

revision = "e6a2b3c4d5f6"
down_revision = "d5f1a2b3c4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("installation_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("installation_jobs.id"), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("storage_key", sa.String(32), nullable=False, unique=True),
        sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_installation_evidence_job_id", "installation_evidence", ["job_id"])


def downgrade():
    op.drop_index("ix_installation_evidence_job_id", table_name="installation_evidence")
    op.drop_table("installation_evidence")
