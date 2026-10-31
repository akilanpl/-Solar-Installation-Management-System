from datetime import date, datetime, time
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.core.security import utcnow
from app.db.session import get_db
from app.models.identity import User
from app.models.scheduling import TechnicianAppointment, TechnicianAvailability, TechnicianLeave
from app.repositories.queries import add_audit
from app.schemas.calendar import AppointmentInput, IntervalInput
from app.services import calendar_service

router = APIRouter(tags=["technician-calendar"])


class AvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: str = Field(max_length=64)
    working_hours: dict[str, list[tuple[str, str]]]
    qualifications: dict[Literal["survey", "installation"], date]
    daily_capacity: int = Field(ge=1, le=20)

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Choose an IANA timezone.") from exc
        return value

    @field_validator("working_hours")
    @classmethod
    def valid_hours(cls, value):
        for day, windows in value.items():
            if day not in [str(i) for i in range(7)]:
                raise ValueError("Use weekday 0 (Monday) through 6.")
            previous = None
            for start, end in sorted(windows):
                a, b = time.fromisoformat(start), time.fromisoformat(end)
                if a.tzinfo or b.tzinfo or b <= a or previous and a < previous:
                    raise ValueError("Working intervals must be ordered, local and nonoverlapping.")
                previous = b
        return value


class AvailabilityResponse(AvailabilityInput):
    model_config = ConfigDict(from_attributes=True)
    technician_user_id: UUID


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    technician_user_id: UUID
    job_id: UUID | None
    survey_id: UUID | None
    starts_at: datetime
    ends_at: datetime
    status: str
    override_reason: str | None


class LeaveInput(IntervalInput):
    reason: str = Field(min_length=5, max_length=1000)


class LeaveResponse(LeaveInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    technician_user_id: UUID


@router.put("/scheduling/availability/{tech_id}", response_model=AvailabilityResponse)
def availability(
    tech_id: UUID,
    payload: AvailabilityInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    if user.role_code != "admin":
        raise AppError(
            403,
            "forbidden",
            "Only admin records independently verified availability/qualifications.",
        )
    calendar_service.technician(db, tech_id)
    row = db.get(TechnicianAvailability, tech_id)
    if row is None:
        row = TechnicianAvailability(technician_user_id=tech_id, recorded_by_user_id=user.id)
        db.add(row)
    for key, value in payload.model_dump(mode="json").items():
        setattr(row, key, value)
    row.recorded_by_user_id = user.id
    row.updated_at = utcnow()
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="technician.availability_recorded",
        entity_type="user",
        entity_id=tech_id,
        metadata=payload.model_dump(mode="json"),
    )
    return row


@router.get("/scheduling/availability/{tech_id}", response_model=AvailabilityResponse)
def read_availability(
    tech_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    if user.role_code not in {"sales", "admin"} and not (
        user.role_code == "technician" and user.id == tech_id
    ):
        raise AppError(403, "forbidden", "Calendar access denied.")
    row = db.get(TechnicianAvailability, tech_id)
    if row is None:
        raise AppError(404, "availability_unknown", "Availability has not been declared.")
    return row


@router.post("/scheduling/leave/{tech_id}", response_model=LeaveResponse)
def leave(
    tech_id: UUID,
    payload: LeaveInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    if user.role_code not in {"admin", "sales"}:
        raise AppError(403, "forbidden", "Only operations can record approved leave.")
    calendar_service.technician(db, tech_id)
    if db.scalar(
        select(TechnicianAppointment.id)
        .where(
            TechnicianAppointment.technician_user_id == tech_id,
            TechnicianAppointment.status == "booked",
            TechnicianAppointment.starts_at < payload.ends_at,
            TechnicianAppointment.ends_at > payload.starts_at,
        )
        .limit(1)
    ):
        raise AppError(
            409, "existing_appointment", "Reassign conflicting appointments before recording leave."
        )
    row = TechnicianLeave(
        technician_user_id=tech_id, recorded_by_user_id=user.id, **payload.model_dump()
    )
    db.add(row)
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="technician.leave_recorded",
        entity_type="technician_leave",
        entity_id=row.id,
        metadata={"reason": payload.reason},
    )
    return row


@router.post("/scheduling/appointments", response_model=AppointmentResponse)
def book(
    payload: AppointmentInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    return calendar_service.book(db, user, payload)


@router.get("/scheduling/appointments", response_model=list[AppointmentResponse])
def appointments(
    user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")
):
    if user.role_code not in {"sales", "admin", "technician"}:
        raise AppError(403, "forbidden", "Calendar access denied.")
    query = select(TechnicianAppointment)
    if user.role_code == "technician":
        query = query.where(TechnicianAppointment.technician_user_id == user.id)
    return list(db.scalars(query.order_by(TechnicianAppointment.starts_at.desc()).limit(200)))


class EligibilityInput(IntervalInput):
    resource_type: Literal["survey", "installation"]


class EligibilityResponse(BaseModel):
    technician_user_id: UUID
    eligible: bool
    reasons: list[str]


@router.post("/scheduling/eligibility", response_model=list[EligibilityResponse])
def eligibility(
    payload: EligibilityInput,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
):
    if user.role_code not in {"sales", "admin"}:
        raise AppError(403, "forbidden", "Only operations can evaluate assignment.")
    rows = []
    for tech_id in db.scalars(
        select(User.id).where(User.is_active.is_(True), User.role_code == "technician")
    ):
        reasons = calendar_service.reasons(
            db, tech_id, payload.resource_type, payload.starts_at, payload.ends_at
        )
        rows.append(
            EligibilityResponse(
                technician_user_id=tech_id,
                eligible=not reasons,
                reasons=reasons
                or [
                    "Declared qualification, hours, capacity and calendar checks passed; travel and geography not evaluated."
                ],
            )
        )
    return rows
