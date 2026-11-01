"""Bookings use declared qualifications/hours; unknown availability fails closed.

Every writer locks the actual technician user row, so independent appointment
requests serialize across surveys and installations. No travel time is invented.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.errors import AppError
from app.models.identity import User
from app.models.phase3 import InstallationJob
from app.models.scheduling import TechnicianAppointment, TechnicianAvailability, TechnicianLeave
from app.models.workflow import Survey
from app.repositories.queries import add_audit


def technician(db, tech_id):
    row = db.scalar(select(User).where(User.id == tech_id).with_for_update())
    if row is None or row.role_code != "technician" or not row.is_active:
        raise AppError(422, "invalid_technician", "Select an active technician.")
    return row


def reasons(db, tech_id, kind, start, end, exclude=None):
    policy = db.get(TechnicianAvailability, tech_id)
    if policy is None:
        return ["Availability and qualifications have not been declared."]
    result = []
    local_start = start.astimezone(ZoneInfo(policy.timezone))
    local_end = end.astimezone(ZoneInfo(policy.timezone))
    valid_until = policy.qualifications.get(kind)
    if not valid_until or datetime.fromisoformat(valid_until).date() < local_end.date():
        result.append("Required job qualification is missing or expired.")
    windows = policy.working_hours.get(str(local_start.weekday()), [])
    if local_start.date() != local_end.date() or not any(
        time.fromisoformat(a) <= local_start.time().replace(tzinfo=None)
        and local_end.time().replace(tzinfo=None) <= time.fromisoformat(b)
        for a, b in windows
    ):
        result.append("Interval is outside declared working hours.")
    if db.scalar(
        select(TechnicianLeave.id)
        .where(
            TechnicianLeave.technician_user_id == tech_id,
            TechnicianLeave.starts_at < end,
            TechnicianLeave.ends_at > start,
        )
        .limit(1)
    ):
        result.append("Recorded leave overlaps the requested interval.")
    query = select(TechnicianAppointment).where(
        TechnicianAppointment.technician_user_id == tech_id,
        TechnicianAppointment.status == "booked",
    )
    if exclude is not None:
        query = query.where(TechnicianAppointment.id != exclude)
    appointments = list(db.scalars(query))
    if any(row.starts_at < end and row.ends_at > start for row in appointments):
        result.append("An existing appointment overlaps the requested interval.")
    if (
        sum(
            row.starts_at.astimezone(ZoneInfo(policy.timezone)).date() == local_start.date()
            for row in appointments
        )
        >= policy.daily_capacity
    ):
        result.append("Declared daily job capacity is exhausted.")
    return result


def book(db, user, payload):
    if user.role_code not in {"sales", "admin"}:
        raise AppError(403, "forbidden", "Only sales/admin can book Phase 3 work.")
    kind = payload.resource_type
    model = InstallationJob if kind == "installation" else Survey
    resource = db.scalar(select(model).where(model.id == payload.resource_id).with_for_update())
    if resource is None:
        raise AppError(404, "not_found", "Work record not found.")
    if resource.status in {
        "completed",
        "cancelled",
        "approved",
        "rejected",
        "submitted",
        "in_progress",
        "en_route",
        "on_site",
    }:
        raise AppError(409, "invalid_transition", "Started or closed work cannot be reassigned.")
    existing_tech = (
        resource.technician_user_id
        if kind == "installation"
        else resource.assigned_technician_user_id
    )
    # Reassignments lock both employees in stable order, then cancel old custody.
    for tech_id in sorted({t for t in [existing_tech, payload.technician_user_id] if t}, key=str):
        db.scalar(select(User).where(User.id == tech_id).with_for_update())
    technician(db, payload.technician_user_id)
    column = (
        TechnicianAppointment.job_id if kind == "installation" else TechnicianAppointment.survey_id
    )
    old = db.scalar(
        select(TechnicianAppointment)
        .where(column == resource.id, TechnicianAppointment.status == "booked")
        .with_for_update()
    )
    if (
        old
        and old.technician_user_id == payload.technician_user_id
        and old.starts_at == payload.starts_at
        and old.ends_at == payload.ends_at
    ):
        return old
    if (
        old or existing_tech and existing_tech != payload.technician_user_id
    ) and not payload.override_reason:
        raise AppError(422, "reason_required", "Record a reason for reassignment or rescheduling.")
    blocked = reasons(
        db,
        payload.technician_user_id,
        kind,
        payload.starts_at,
        payload.ends_at,
        old.id if old else None,
    )
    # Overrides explain changes; they never bypass active/skill/leave/overlap safety.
    if blocked:
        raise AppError(409, "technician_ineligible", " ".join(blocked))
    if old:
        old.status = "cancelled"
    row = TechnicianAppointment(
        technician_user_id=payload.technician_user_id,
        job_id=resource.id if kind == "installation" else None,
        survey_id=resource.id if kind == "survey" else None,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status="booked",
        override_reason=payload.override_reason,
        recorded_by_user_id=user.id,
    )
    db.add(row)
    if kind == "installation":
        resource.technician_user_id = payload.technician_user_id
        resource.slot_starts_at = payload.starts_at
        resource.status = "scheduled"
    else:
        resource.assigned_technician_user_id = payload.technician_user_id
        resource.appointment_starts_at = payload.starts_at
        resource.appointment_status = "confirmed"
        resource.status = "assigned"
    db.flush()
    add_audit(
        db,
        actor_user_id=user.id,
        action="appointment.booked",
        entity_type="technician_appointment",
        entity_id=row.id,
        metadata={
            "resource_type": kind,
            "resource_id": str(resource.id),
            "reason": payload.override_reason,
            "travel": "not evaluated; verified coordinates/routing unavailable",
        },
    )
    return row
