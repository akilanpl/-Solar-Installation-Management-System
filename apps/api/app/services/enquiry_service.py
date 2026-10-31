"""Customer enquiry creation and sales qualification.

Money is integer paise (`monthly_bill_minor`). Capacity is integer watts.
Both are validated again by database check constraints.
"""

import json
import uuid
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.enquiry import (
    QUALIFICATION_TRANSITIONS,
    CustomerSite,
    Enquiry,
    EnquiryCounter,
    EnquiryStatusHistory,
)
from app.models.identity import User
from app.repositories.queries import add_audit, enquiry_by_idempotency, get_enquiry
from app.schemas import EnquiryCreate, QualificationUpdate
from app.services.survey_service import approved_survey_exists


def _request_hash(payload: EnquiryCreate) -> str:
    raw = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def _next_reference(db: Session) -> str:
    year = utcnow().year
    statement = (
        pg_insert(EnquiryCounter)
        .values(year=year, last_value=1)
        .on_conflict_do_update(
            index_elements=[EnquiryCounter.year],
            set_={"last_value": EnquiryCounter.last_value + 1},
        )
        .returning(EnquiryCounter.last_value)
    )
    value = int(db.execute(statement).scalar_one())
    return f"ENQ-{year}-{value:06d}"


def create_enquiry(
    db: Session,
    user: User,
    payload: EnquiryCreate,
    idempotency_key: str,
) -> tuple[Enquiry, bool]:
    if user.role_code != "customer" or user.customer_profile is None:
        raise AppError(403, "forbidden", "Only a customer can submit an enquiry.")
    digest = _request_hash(payload)
    existing = enquiry_by_idempotency(db, user.id, idempotency_key)
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(
                409,
                "idempotency_conflict",
                "This Idempotency-Key was already used for a different enquiry.",
            )
        loaded = get_enquiry(db, existing.id)
        if loaded is None:
            raise AppError(500, "enquiry_missing", "The saved enquiry could not be reloaded.")
        return loaded, True

    site = CustomerSite(
        customer_user_id=user.id,
        line1=payload.site.line1,
        line2=payload.site.line2,
        city=payload.site.city,
        state=payload.site.state,
        postal_code=payload.site.postal_code,
        country_code="IN",
    )
    db.add(site)
    db.flush()
    enquiry = Enquiry(
        reference=_next_reference(db),
        customer_user_id=user.id,
        site_id=site.id,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        preferred_capacity_w=payload.preferred_capacity_w,
        grid_preference=payload.grid_preference,
        monthly_bill_minor=payload.monthly_bill_minor,
        currency_code="INR",
        subsidy_interest=payload.subsidy_interest,
        status="submitted",
        idempotency_key=idempotency_key,
        request_hash=digest,
    )
    db.add(enquiry)
    db.flush()
    db.add(
        EnquiryStatusHistory(
            enquiry_id=enquiry.id,
            from_status=None,
            to_status="submitted",
            actor_user_id=user.id,
            note=None,
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="enquiry.created",
        entity_type="enquiry",
        entity_id=enquiry.id,
        metadata={"reference": enquiry.reference, "status": "submitted"},
    )
    loaded = get_enquiry(db, enquiry.id)
    if loaded is None:
        raise AppError(500, "enquiry_missing", "The enquiry was not saved.")
    return loaded, False


def get_visible_enquiry(db: Session, user: User, enquiry_id: uuid.UUID) -> Enquiry:
    if user.role_code not in {"customer", "sales", "admin"}:
        raise AppError(403, "forbidden", "You do not have access to enquiries.")
    enquiry = get_enquiry(db, enquiry_id)
    if enquiry is None:
        raise AppError(404, "not_found", "Enquiry not found.")
    if user.role_code == "customer" and enquiry.customer_user_id != user.id:
        raise AppError(404, "not_found", "Enquiry not found.")
    return enquiry


def list_visible_enquiries(
    db: Session, user: User, *, page: int, page_size: int
) -> tuple[list[Enquiry], int]:
    if user.role_code not in {"customer", "sales", "admin"}:
        raise AppError(403, "forbidden", "You do not have access to enquiries.")
    query = select(Enquiry)
    count_query = select(func.count()).select_from(Enquiry)
    if user.role_code == "customer":
        query = query.where(Enquiry.customer_user_id == user.id)
        count_query = count_query.where(Enquiry.customer_user_id == user.id)
    total = int(db.scalar(count_query) or 0)
    rows = list(
        db.scalars(
            query.order_by(Enquiry.created_at.desc(), Enquiry.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total


def qualify_enquiry(
    db: Session, user: User, enquiry_id: uuid.UUID, payload: QualificationUpdate
) -> Enquiry:
    if user.role_code not in {"sales", "admin"}:
        raise AppError(403, "forbidden", "Only sales can update qualification.")
    enquiry = get_enquiry(db, enquiry_id)
    if enquiry is None:
        raise AppError(404, "not_found", "Enquiry not found.")
    allowed = QUALIFICATION_TRANSITIONS[enquiry.status]
    if payload.status not in allowed:
        raise AppError(
            409,
            "invalid_transition",
            f"Cannot move an enquiry from {enquiry.status} to {payload.status}.",
            details=[{"field": "status", "message": f"Allowed: {', '.join(sorted(allowed))}"}],
        )
    if payload.status == "not_qualified" and (payload.note is None or len(payload.note) < 3):
        raise AppError(
            422,
            "validation_error",
            "A short note is required when an enquiry is not qualified.",
            details=[{"field": "note", "message": "Explain why the enquiry is not qualified."}],
        )
    if payload.status == "qualified":
        area = (
            payload.shadow_free_area_sqm
            if payload.shadow_free_area_sqm is not None
            else enquiry.shadow_free_area_sqm
        )
        suitable = (
            payload.grid_connection_suitable
            if payload.grid_connection_suitable is not None
            else enquiry.grid_connection_suitable
        )
        if area is None or suitable is None:
            raise AppError(
                422,
                "validation_error",
                "Qualification needs the shadow-free area and grid suitability.",
                details=[
                    {
                        "field": "shadow_free_area_sqm",
                        "message": "Required when qualifying an enquiry.",
                    }
                ],
            )
    if approved_survey_exists(db, enquiry.id) and not payload.acknowledge_downstream:
        area_changed = (
            payload.shadow_free_area_sqm is not None
            and payload.shadow_free_area_sqm != enquiry.shadow_free_area_sqm
        )
        grid_changed = (
            payload.grid_connection_suitable is not None
            and payload.grid_connection_suitable != enquiry.grid_connection_suitable
        )
        if area_changed or grid_changed:
            raise AppError(
                409,
                "qualification_locked",
                "An approved survey already exists. Repeat the update with "
                "acknowledge_downstream to record the change without altering "
                "that survey or any quotation.",
            )
    previous = enquiry.status
    enquiry.status = payload.status
    enquiry.qualification_note = payload.note
    if payload.shadow_free_area_sqm is not None:
        enquiry.shadow_free_area_sqm = payload.shadow_free_area_sqm
    if payload.grid_connection_suitable is not None:
        enquiry.grid_connection_suitable = payload.grid_connection_suitable
    if payload.status in {"qualified", "not_qualified"}:
        enquiry.decision_by_user_id = user.id
        enquiry.decision_at = utcnow()
    enquiry.updated_at = utcnow()
    db.add(
        EnquiryStatusHistory(
            enquiry_id=enquiry.id,
            from_status=previous,
            to_status=payload.status,
            actor_user_id=user.id,
            note=payload.note,
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="enquiry.qualification_updated",
        entity_type="enquiry",
        entity_id=enquiry.id,
        metadata={
            "from_status": previous,
            "to_status": payload.status,
            "acknowledge_downstream": payload.acknowledge_downstream,
            "downstream_records_rewritten": False,
        },
    )
    db.flush()
    reloaded = get_enquiry(db, enquiry.id)
    if reloaded is None:
        raise AppError(500, "enquiry_missing", "The enquiry could not be reloaded.")
    return reloaded
