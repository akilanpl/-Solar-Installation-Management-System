"""Explicit availability declarations and cross-job-type appointments."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TechnicianAvailability(Base):
    __tablename__ = "technician_availability"
    __table_args__ = (
        CheckConstraint("daily_capacity > 0 AND daily_capacity <= 20", name="capacity"),
    )
    technician_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    working_hours: Mapped[dict] = mapped_column(JSONB, nullable=False)
    qualifications: Mapped[dict] = mapped_column(JSONB, nullable=False)
    daily_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TechnicianLeave(Base):
    __tablename__ = "technician_leave"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="interval"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    technician_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class TechnicianAppointment(Base):
    __tablename__ = "technician_appointments"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="interval"),
        CheckConstraint("status IN ('booked','cancelled')", name="status"),
        CheckConstraint("(job_id IS NULL) <> (survey_id IS NULL)", name="one_resource"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    technician_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("installation_jobs.id"))
    survey_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("surveys.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
