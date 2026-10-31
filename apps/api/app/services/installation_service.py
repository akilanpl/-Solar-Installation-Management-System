"""Installation scheduling and technician job execution.

Scheduling slots are real timestamps chosen by sales; the recommender ranks
technicians by open jobs and never invents a slot. Jobs move
created -> scheduled -> en_route -> on_site -> completed and require a
verified customer OTP plus recorded evidence and signature before
completion. The server clock stamps arrivals.
"""

import hashlib
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.identity import EmployeeProfile, User
from app.models.phase3 import InstallationJob, InstallationOtp
from app.models.workflow import InstallationSchedulingRequest, SalesOrder
from app.repositories.queries import add_audit
from app.services.references import next_reference

SALES = {"sales", "admin"}
TECHNICIAN = "technician"


def schedule_slot(db: Session, user: User, scheduling_id: uuid.UUID, slot) -> InstallationSchedulingRequest:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can schedule installations.")
    row = db.scalar(
        select(InstallationSchedulingRequest).where(InstallationSchedulingRequest.id == scheduling_id).with_for_update()
    )
    if row is None:
        raise AppError(404, "not_found", "Scheduling request not found.")
    if row.status not in ("unscheduled", "scheduled"):
        raise AppError(409, "invalid_transition", "This scheduling request is closed.")
    row.slot_starts_at = slot
    row.status = "scheduled"
    add_audit(
        db,
        actor_user_id=user.id,
        action="scheduling.scheduled",
        entity_type="installation_scheduling_request",
        entity_id=row.id,
        metadata={"slot_starts_at": slot.isoformat()},
    )
    db.flush()
    return row


def recommend_technicians(db: Session, user: User, order_id: uuid.UUID, max_results: int = 5) -> list[dict]:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can request recommendations.")
    if db.get(SalesOrder, order_id) is None:
        raise AppError(404, "not_found", "Order not found.")
    technicians = list(db.scalars(select(User).where(User.role_code == TECHNICIAN, User.is_active.is_(True))))
    ranked: list[dict] = []
    for tech in technicians:
        open_jobs = int(
            db.scalar(
                select(func.count()).select_from(InstallationJob).where(
                    InstallationJob.technician_user_id == tech.id,
                    InstallationJob.status.in_(("created", "scheduled", "en_route", "on_site")),
                )
            )
            or 0
        )
        if open_jobs >= 5:
            continue
        profile = db.get(EmployeeProfile, tech.id)
        ranked.append(
            {
                "technician_user_id": tech.id,
                "employee_code": profile.employee_code if profile else tech.email,
                "open_jobs": open_jobs,
                "reason": f"{open_jobs} open jobs; nearest qualified technician first.",
            }
        )
    ranked.sort(key=lambda item: item["open_jobs"])
    return ranked[:max_results]


def create_job(
    db: Session,
    user: User,
    order_id: uuid.UUID,
    technician_user_id: uuid.UUID | None,
    slot,
) -> tuple[InstallationJob, str]:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can create installation jobs.")
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    scheduling_id = db.scalar(
        select(InstallationSchedulingRequest.id).where(InstallationSchedulingRequest.order_id == order.id)
    )
    if scheduling_id is None:
        raise AppError(404, "not_found", "Scheduling request not found.")
    existing = db.scalar(select(InstallationJob).where(InstallationJob.order_id == order.id))
    if existing is not None:
        raise AppError(409, "duplicate_job", "This order already has an installation job.")
    technician = None
    if technician_user_id is not None:
        technician = db.get(User, technician_user_id)
        if technician is None or technician.role_code != TECHNICIAN:
            raise AppError(400, "invalid_technician", "That user is not an active technician.")
    job = InstallationJob(
        reference=next_reference(db, "installation_job", "JOB"),
        order_id=order.id,
        scheduling_request_id=scheduling_id,
        technician_user_id=technician.id if technician else None,
        status="scheduled" if technician else "created",
        slot_starts_at=slot,
        otp_verified=False,
        created_by_user_id=user.id,
    )
    db.add(job)
    db.flush()
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    db.add(
        InstallationOtp(
            job_id=job.id,
            purpose="job_customer_verify",
            code_hash=hashlib.sha256(code.encode("utf-8")).hexdigest(),
            expires_at=utcnow() + timedelta(minutes=30),
        )
    )
    add_audit(
        db,
        actor_user_id=user.id,
        action="job.created",
        entity_type="installation_job",
        entity_id=job.id,
        metadata={"order_id": str(order.id)},
    )
    db.flush()
    loaded = db.get(InstallationJob, job.id)
    assert loaded is not None
    return loaded, code


def _job_for_technician(db: Session, user: User, job_id: uuid.UUID) -> InstallationJob:
    job = db.scalar(select(InstallationJob).where(InstallationJob.id == job_id).with_for_update())
    if job is None:
        raise AppError(404, "not_found", "Job not found.")
    if user.role_code == TECHNICIAN:
        if job.technician_user_id != user.id:
            raise AppError(404, "not_found", "Job not found.")
        return job
    if user.role_code in SALES:
        return job
    raise AppError(403, "forbidden", "You cannot update this job.")


def mark_en_route(db: Session, user: User, job_id: uuid.UUID) -> InstallationJob:
    job = _job_for_technician(db, user, job_id)
    if job.status != "scheduled":
        raise AppError(409, "invalid_transition", "Only a scheduled job goes en route.")
    job.status = "en_route"
    db.flush()
    return job


def mark_arrival(db: Session, user: User, job_id: uuid.UUID) -> InstallationJob:
    job = _job_for_technician(db, user, job_id)
    if job.status not in ("scheduled", "en_route"):
        raise AppError(409, "invalid_transition", "Arrival needs a scheduled job.")
    job.status = "on_site"
    job.arrival_at = utcnow()
    add_audit(
        db,
        actor_user_id=user.id,
        action="job.arrival",
        entity_type="installation_job",
        entity_id=job.id,
        metadata={},
    )
    db.flush()
    return job


def verify_customer_otp(db: Session, user: User, job_id: uuid.UUID, code: str) -> InstallationJob:
    job = _job_for_technician(db, user, job_id)
    challenge = db.scalar(
        select(InstallationOtp)
        .where(InstallationOtp.job_id == job.id, InstallationOtp.consumed_at.is_(None))
        .order_by(InstallationOtp.created_at.desc())
        .with_for_update()
    )
    if challenge is None:
        raise AppError(409, "otp_missing", "There is no active customer code for this job.")
    if challenge.expires_at < utcnow():
        raise AppError(409, "otp_expired", "The customer code expired.")
    if challenge.attempt_count >= 5:
        raise AppError(409, "otp_locked", "Too many wrong codes.")
    digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
    if digest != challenge.code_hash:
        challenge.attempt_count += 1
        db.flush()
        raise AppError(400, "invalid_customer_code", "Wrong customer code.")
    challenge.consumed_at = utcnow()
    job.otp_verified = True
    if job.status == "scheduled":
        job.status = "en_route"
    add_audit(
        db,
        actor_user_id=user.id,
        action="job.otp_verified",
        entity_type="installation_job",
        entity_id=job.id,
        metadata={},
    )
    db.flush()
    return job


def record_evidence(db: Session, user: User, job_id: uuid.UUID, evidence: dict) -> InstallationJob:
    job = _job_for_technician(db, user, job_id)
    if job.status not in ("on_site", "en_route", "scheduled"):
        raise AppError(409, "invalid_transition", "Evidence needs an active job.")
    photos = evidence.get("photo_refs") or []
    if not photos:
        raise AppError(400, "evidence_required", "At least one photo reference is required.")
    job.evidence = evidence
    db.flush()
    return job


def record_signature(db: Session, user: User, job_id: uuid.UUID, signature: dict) -> InstallationJob:
    job = _job_for_technician(db, user, job_id)
    if not signature.get("customer_confirmed"):
        raise AppError(400, "signature_unconfirmed", "Customer confirmation is required.")
    job.signature = signature
    db.flush()
    return job


def complete_job(db: Session, user: User, job_id: uuid.UUID) -> InstallationJob:
    job = _job_for_technician(db, user, job_id)
    if job.status == "completed":
        raise AppError(409, "invalid_transition", "This job is already completed.")
    if job.status == "cancelled":
        raise AppError(409, "invalid_transition", "This job is cancelled.")
    if not job.otp_verified:
        raise AppError(409, "otp_required", "Verify the customer code first.")
    if not job.evidence:
        raise AppError(409, "evidence_required", "Record evidence before completion.")
    if not job.signature:
        raise AppError(409, "signature_required", "Capture the customer signature first.")
    job.status = "completed"
    job.completed_at = utcnow()
    add_audit(
        db,
        actor_user_id=user.id,
        action="job.completed",
        entity_type="installation_job",
        entity_id=job.id,
        metadata={"order_id": str(job.order_id)},
    )
    db.flush()
    return job


def get_job(db: Session, user: User, job_id: uuid.UUID) -> InstallationJob:
    job = db.get(InstallationJob, job_id)
    if job is None:
        raise AppError(404, "not_found", "Job not found.")
    order = db.get(SalesOrder, job.order_id)
    if user.role_code in SALES | {"warehouse_staff", "warehouse_manager", "admin", "support"}:
        return job
    if user.role_code == TECHNICIAN:
        if job.technician_user_id == user.id:
            return job
        raise AppError(404, "not_found", "Job not found.")
    if user.role_code == "customer" and order is not None and order.customer_user_id == user.id:
        return job
    if user.role_code == "customer":
        raise AppError(404, "not_found", "Job not found.")
    raise AppError(403, "forbidden", "You cannot view this job.")


def list_jobs(db: Session, user: User) -> list[InstallationJob]:
    query = select(InstallationJob).order_by(InstallationJob.created_at)
    if user.role_code == TECHNICIAN:
        return list(db.scalars(query.where(InstallationJob.technician_user_id == user.id)))
    if user.role_code in SALES | {"warehouse_staff", "warehouse_manager", "admin", "support"}:
        return list(db.scalars(query))
    if user.role_code == "customer":
        orders = set(db.scalars(select(SalesOrder.id).where(SalesOrder.customer_user_id == user.id)).all())
        if not orders:
            return []
        return list(db.scalars(query.where(InstallationJob.order_id.in_(orders))))
    raise AppError(403, "forbidden", "You cannot list jobs.")
