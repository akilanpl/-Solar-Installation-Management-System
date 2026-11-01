"""Rooftop survey lifecycle.

draft → assigned → in_progress → submitted → approved or rejected.

Only the assigned technician submits. Only sales or admin approves.
A rejected survey stays rejected; a correction is a new survey revision.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.enquiry import Enquiry
from app.models.identity import User
from app.models.workflow import Survey, SurveyEvidence, SurveyStatusHistory
from app.repositories.queries import add_audit, get_enquiry
from app.schemas.workflow import SurveyAssignment, SurveyDecision, SurveySubmit
from app.services.references import next_reference

OPEN_STATUSES = ("draft", "assigned", "in_progress", "submitted", "approved")
SALES = {"sales", "admin"}


def _load(db: Session, survey_id: uuid.UUID) -> Survey | None:
    return db.scalar(
        select(Survey)
        .where(Survey.id == survey_id)
        .options(selectinload(Survey.history), selectinload(Survey.evidence))
        .execution_options(populate_existing=True)
    )


def _visible(user: User, survey: Survey) -> Survey:
    if user.role_code in SALES:
        return survey
    if user.role_code == "customer" and survey.customer_user_id == user.id:
        return survey
    if user.role_code == "technician" and survey.assigned_technician_user_id == user.id:
        return survey
    if user.role_code in {"customer", "technician"}:
        raise AppError(404, "not_found", "Survey not found.")
    raise AppError(403, "forbidden", "You cannot view this survey.")


def get_survey(db: Session, user: User, survey_id: uuid.UUID) -> Survey:
    survey = _load(db, survey_id)
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    return _visible(user, survey)


def list_surveys(db: Session, user: User, *, page: int, page_size: int) -> tuple[list[Survey], int]:
    query = select(Survey).options(selectinload(Survey.history), selectinload(Survey.evidence))
    count_query = select(func.count()).select_from(Survey)
    if user.role_code == "customer":
        query = query.where(Survey.customer_user_id == user.id)
        count_query = count_query.where(Survey.customer_user_id == user.id)
    elif user.role_code == "technician":
        query = query.where(Survey.assigned_technician_user_id == user.id)
        count_query = count_query.where(Survey.assigned_technician_user_id == user.id)
    elif user.role_code not in SALES:
        raise AppError(403, "forbidden", "You cannot list surveys.")
    total = int(db.scalar(count_query) or 0)
    rows = list(
        db.scalars(
            query.order_by(Survey.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return rows, total


def _transition(
    db: Session,
    survey: Survey,
    actor: User,
    to_status: str,
    note: str | None,
) -> None:
    previous = survey.status
    survey.status = to_status
    survey.updated_at = utcnow()
    db.add(
        SurveyStatusHistory(
            survey_id=survey.id,
            from_status=previous,
            to_status=to_status,
            actor_user_id=actor.id,
            note=note,
        )
    )


def _ensure_no_open_survey(db: Session, enquiry_id: uuid.UUID) -> None:
    existing = db.scalar(
        select(Survey.id).where(
            Survey.enquiry_id == enquiry_id,
            Survey.status.in_(OPEN_STATUSES),
        )
    )
    if existing is not None:
        raise AppError(
            409,
            "survey_exists",
            "This enquiry already has a survey that is not rejected.",
        )


def create_survey(db: Session, user: User, enquiry_id: uuid.UUID) -> Survey:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can open a survey.")
    enquiry = get_enquiry(db, enquiry_id)
    if enquiry is None:
        raise AppError(404, "not_found", "Enquiry not found.")
    if enquiry.status != "qualified":
        raise AppError(
            409,
            "enquiry_not_qualified",
            "A survey can be opened only from a qualified enquiry.",
        )
    _ensure_no_open_survey(db, enquiry.id)
    survey = Survey(
        reference=next_reference(db, "survey", "SUR"),
        enquiry_id=enquiry.id,
        customer_user_id=enquiry.customer_user_id,
        site_id=enquiry.site_id,
        appointment_status="pending",
        status="draft",
        revision_number=_next_revision(db, enquiry.id),
        created_by_user_id=user.id,
    )
    db.add(survey)
    db.flush()
    db.add(
        SurveyStatusHistory(
            survey_id=survey.id,
            from_status=None,
            to_status="draft",
            actor_user_id=user.id,
            note=None,
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="survey.created",
        entity_type="survey",
        entity_id=survey.id,
        metadata={"enquiry_id": str(enquiry.id)},
    )
    db.flush()
    loaded = _load(db, survey.id)
    if loaded is None:
        raise AppError(500, "survey_missing", "The survey could not be reloaded.")
    return loaded


def _next_revision(db: Session, enquiry_id: uuid.UUID) -> int:
    current = db.scalar(
        select(func.max(Survey.revision_number)).where(Survey.enquiry_id == enquiry_id)
    )
    return int(current or 0) + 1


def assign_survey(
    db: Session, user: User, survey_id: uuid.UUID, payload: SurveyAssignment
) -> Survey:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can assign a survey.")
    survey = _load(db, survey_id)
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    if survey.status not in {"draft", "assigned"}:
        raise AppError(409, "invalid_transition", "This survey can no longer be assigned.")
    technician = db.get(User, payload.technician_user_id)
    if technician is None or technician.role_code != "technician" or not technician.is_active:
        raise AppError(422, "validation_error", "Choose an active technician.")
    from app.models.scheduling import TechnicianAppointment

    if payload.appointment_starts_at is not None or db.scalar(
        select(TechnicianAppointment.id)
        .where(
            TechnicianAppointment.survey_id == survey.id, TechnicianAppointment.status == "booked"
        )
        .limit(1)
    ):
        raise AppError(
            409,
            "use_calendar_booking",
            "Use the calendar with an explicit start/end interval to book or reschedule this survey.",
        )
    survey.assigned_technician_user_id = technician.id
    if payload.appointment_starts_at is None:
        survey.appointment_status = "pending"
        survey.appointment_starts_at = None
    else:
        survey.appointment_status = "confirmed"
        survey.appointment_starts_at = payload.appointment_starts_at
    _transition(db, survey, user, "assigned", None)
    add_audit(
        db,
        actor_user_id=user.id,
        action="survey.assigned",
        entity_type="survey",
        entity_id=survey.id,
        metadata={
            "technician_user_id": str(technician.id),
            "appointment_status": survey.appointment_status,
        },
    )
    db.flush()
    return _require(db, survey.id)


def start_survey(db: Session, user: User, survey_id: uuid.UUID) -> Survey:
    survey = _load(db, survey_id)
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    if user.role_code != "technician" or survey.assigned_technician_user_id != user.id:
        raise AppError(403, "forbidden", "Only the assigned technician can start this survey.")
    if survey.status != "assigned":
        raise AppError(409, "invalid_transition", "Only an assigned survey can be started.")
    _transition(db, survey, user, "in_progress", None)
    db.flush()
    return _require(db, survey.id)


def submit_survey(db: Session, user: User, survey_id: uuid.UUID, payload: SurveySubmit) -> Survey:
    survey = _load(db, survey_id)
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    if user.role_code != "technician" or survey.assigned_technician_user_id != user.id:
        raise AppError(403, "forbidden", "Only the assigned technician can submit this survey.")
    if survey.status != "in_progress":
        raise AppError(409, "invalid_transition", "Start the survey before submitting it.")
    survey.azimuth_deg = payload.azimuth_deg
    survey.tilt_deg = payload.tilt_deg
    survey.shadow_free_area_sqm = payload.shadow_free_area_sqm
    survey.cable_distance_m = payload.cable_distance_m
    survey.grid_connection = payload.grid_connection
    survey.notes = payload.notes
    survey.submitted_at = utcnow()
    _transition(db, survey, user, "submitted", None)
    add_audit(
        db,
        actor_user_id=user.id,
        action="survey.submitted",
        entity_type="survey",
        entity_id=survey.id,
        metadata={"cable_distance_m": str(payload.cable_distance_m)},
    )
    db.flush()
    return _require(db, survey.id)


def decide_survey(db: Session, user: User, survey_id: uuid.UUID, payload: SurveyDecision) -> Survey:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can approve or reject a survey.")
    survey = _load(db, survey_id)
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    if survey.status != "submitted":
        raise AppError(409, "invalid_transition", "Only a submitted survey can be reviewed.")
    if payload.decision == "rejected" and (payload.note is None or len(payload.note) < 3):
        raise AppError(
            422,
            "validation_error",
            "A rejection needs a short note.",
            details=[{"field": "note", "message": "Explain what must be corrected."}],
        )
    survey.reviewed_at = utcnow()
    survey.reviewed_by_user_id = user.id
    _transition(db, survey, user, payload.decision, payload.note)
    add_audit(
        db,
        actor_user_id=user.id,
        action=f"survey.{payload.decision}",
        entity_type="survey",
        entity_id=survey.id,
        metadata={"decision": payload.decision},
    )
    db.flush()
    return _require(db, survey.id)


def resurvey(db: Session, user: User, survey_id: uuid.UUID) -> Survey:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can open a resurvey.")
    survey = _load(db, survey_id)
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    if survey.status != "rejected":
        raise AppError(409, "invalid_transition", "Only a rejected survey can be resurveyed.")
    enquiry = db.get(Enquiry, survey.enquiry_id)
    if enquiry is None or enquiry.status != "qualified":
        raise AppError(409, "enquiry_not_qualified", "The enquiry must still be qualified.")
    _ensure_no_open_survey(db, survey.enquiry_id)
    created = Survey(
        reference=next_reference(db, "survey", "SUR"),
        enquiry_id=survey.enquiry_id,
        customer_user_id=survey.customer_user_id,
        site_id=survey.site_id,
        appointment_status="pending",
        status="draft",
        revision_number=_next_revision(db, survey.enquiry_id),
        revision_of_survey_id=survey.id,
        created_by_user_id=user.id,
    )
    db.add(created)
    db.flush()
    db.add(
        SurveyStatusHistory(
            survey_id=created.id,
            from_status=None,
            to_status="draft",
            actor_user_id=user.id,
            note=f"Resurvey of {survey.reference}",
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="survey.resurvey_opened",
        entity_type="survey",
        entity_id=created.id,
        metadata={"previous_survey_id": str(survey.id)},
    )
    db.flush()
    return _require(db, created.id)


def add_evidence(
    db: Session,
    user: User,
    survey_id: uuid.UUID,
    *,
    storage_key: str,
    content_type: str,
    size_bytes: int,
    original_filename: str,
) -> SurveyEvidence:
    survey = _load(db, survey_id)
    if survey is None:
        raise AppError(404, "not_found", "Survey not found.")
    if user.role_code != "technician" or survey.assigned_technician_user_id != user.id:
        raise AppError(403, "forbidden", "Only the assigned technician can add evidence.")
    if survey.status not in {"assigned", "in_progress", "submitted"}:
        raise AppError(409, "invalid_transition", "Evidence cannot be added in this state.")
    safe_name = original_filename.replace("/", " ").replace("\\", " ")[:200] or "evidence"
    row = SurveyEvidence(
        survey_id=survey.id,
        storage_key=storage_key,
        original_filename=safe_name,
        content_type=content_type,
        size_bytes=size_bytes,
        uploaded_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


def _require(db: Session, survey_id: uuid.UUID) -> Survey:
    loaded = _load(db, survey_id)
    if loaded is None:
        raise AppError(500, "survey_missing", "The survey could not be reloaded.")
    return loaded


def approved_survey_exists(db: Session, enquiry_id: uuid.UUID) -> bool:
    found = db.scalar(
        select(Survey.id).where(Survey.enquiry_id == enquiry_id, Survey.status == "approved")
    )
    return found is not None
