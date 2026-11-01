"""Explicit availability, leave and cross-type appointment custody."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "a8c4d5e6f7b8"
down_revision = "f7b3c4d5e6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "technician_availability",
        sa.Column("technician_user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("working_hours", JSONB, nullable=False),
        sa.Column("qualifications", JSONB, nullable=False),
        sa.Column("daily_capacity", sa.Integer(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "daily_capacity > 0 AND daily_capacity <= 20",
            name=op.f("ck_technician_availability_capacity"),
        ),
    )
    op.create_table(
        "technician_leave",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("technician_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_technician_leave_interval")),
    )
    op.create_index(
        "ix_technician_leave_technician_user_id", "technician_leave", ["technician_user_id"]
    )
    op.create_table(
        "technician_appointments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("technician_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("installation_jobs.id")),
        sa.Column("survey_id", sa.Uuid(), sa.ForeignKey("surveys.id")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("override_reason", sa.Text()),
        sa.Column("recorded_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_technician_appointments_interval")),
        sa.CheckConstraint(
            "status IN ('booked','cancelled')", name=op.f("ck_technician_appointments_status")
        ),
        sa.CheckConstraint(
            "(job_id IS NULL) <> (survey_id IS NULL)",
            name=op.f("ck_technician_appointments_one_resource"),
        ),
    )
    op.create_index(
        "ix_technician_appointments_technician_user_id",
        "technician_appointments",
        ["technician_user_id"],
    )


def downgrade():
    for table in ["technician_appointments", "technician_leave", "technician_availability"]:
        if op.get_bind().scalar(sa.text("SELECT count(*) FROM " + table)):
            raise RuntimeError(
                "Refusing to discard scheduling history; restore a verified isolated backup."
            )
    op.drop_table("technician_appointments")
    op.drop_table("technician_leave")
    op.drop_table("technician_availability")
