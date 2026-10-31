"""Installation scheduling and technician job execution.

Scheduling slots are real timestamps chosen by sales; the recommender ranks
technicians by open jobs and never invents a slot. Jobs move
created -> scheduled -> en_route -> on_site -> completed and require a
verified customer OTP plus recorded evidence and signature before
completion. The server clock stamps arrivals.
"""

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import hash_secret, secrets_match, utcnow
from app.models.identity import EmployeeProfile, User
from app.models.phase3 import (
    EquipmentSerial,
    InstallationEvidence,
    InstallationJob,
    InstallationOtp,
)
from app.models.workflow import InstallationSchedulingRequest, SalesOrder
from app.repositories.queries import add_audit
from app.services.evidence_store import evidence_file
from app.services.references import next_reference

SALES = {"sales", "admin"}
TECHNICIAN = "technician"


def schedule_slot(
    db: Session, user: User, scheduling_id: uuid.UUID, slot
) -> InstallationSchedulingRequest:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can schedule installations.")
    row = db.scalar(
        select(InstallationSchedulingRequest)
        .where(InstallationSchedulingRequest.id == scheduling_id)
        .with_for_update()
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


def recommend_technicians(
    db: Session, user: User, order_id: uuid.UUID, max_results: int = 5
) -> list[dict]:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can request recommendations.")
    if db.get(SalesOrder, order_id) is None:
        raise AppError(404, "not_found", "Order not found.")
    technicians = list(
        db.scalars(select(User).where(User.role_code == TECHNICIAN, User.is_active.is_(True)))
    )
    ranked: list[dict] = []
    for tech in technicians:
        open_jobs = int(
            db.scalar(
                select(func.count())
                .select_from(InstallationJob)
                .where(
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
                "reason": f"{open_jobs} open jobs; workload ranking only. Skills, travel and availability are not verified.",
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
    slot_end=None,
) -> tuple[InstallationJob, str]:
    if user.role_code not in SALES:
        raise AppError(403, "forbidden", "Only sales can create installation jobs.")
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise AppError(404, "not_found", "Order not found.")
    scheduling_id = db.scalar(
        select(InstallationSchedulingRequest.id).where(
            InstallationSchedulingRequest.order_id == order.id
        )
    )
    if scheduling_id is None:
        raise AppError(404, "not_found", "Scheduling request not found.")
    existing = db.scalar(select(InstallationJob).where(InstallationJob.order_id == order.id))
    if existing is not None:
        raise AppError(409, "duplicate_job", "This order already has an installation job.")
    technician = None
    if technician_user_id is not None:
        technician = db.get(User, technician_user_id)
        if technician is None or technician.role_code != TECHNICIAN or not technician.is_active:
            raise AppError(400, "invalid_technician", "That user is not an active technician.")
    job = InstallationJob(
        reference=next_reference(db, "installation_job", "JOB"),
        order_id=order.id,
        scheduling_request_id=scheduling_id,
        technician_user_id=technician.id if technician else None,
        status="created",
        slot_starts_at=None,
        otp_verified=False,
        created_by_user_id=user.id,
    )
    db.add(job)
    db.flush()
    if slot is not None:
        if slot_end is None or technician is None:
            raise AppError(
                422,
                "booking_interval_required",
                "Choose a technician and explicit start/end interval.",
            )
        from app.schemas.calendar import AppointmentInput
        from app.services.calendar_service import book

        book(
            db,
            user,
            AppointmentInput(
                resource_type="installation",
                resource_id=job.id,
                technician_user_id=technician.id,
                starts_at=slot,
                ends_at=slot_end,
            ),
        )
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    db.add(
        InstallationOtp(
            job_id=job.id,
            purpose="job_customer_verify",
            code_hash=hash_secret(
                f"{job.id}:job_customer_verify:{code}", get_settings().secret_key
            ),
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
    raise AppError(403, "forbidden", "Only the assigned technician can update this job.")


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
    # A separate transaction owns only challenge state. Never commit the caller's
    # pending business mutations to preserve a rejected attempt.
    failure = None
    with Session(db.get_bind(), expire_on_commit=False) as security_db:
        with security_db.begin():
            challenge = security_db.scalar(
                select(InstallationOtp)
                .where(InstallationOtp.job_id == job.id, InstallationOtp.consumed_at.is_(None))
                .order_by(InstallationOtp.created_at.desc())
                .with_for_update()
            )
            if challenge is None:
                failure = AppError(
                    409, "otp_missing", "There is no active customer code for this job."
                )
            elif challenge.expires_at <= utcnow():
                failure = AppError(409, "otp_expired", "The customer code expired.")
            elif challenge.attempt_count >= 5:
                failure = AppError(409, "otp_locked", "Too many wrong codes.")
            elif not secrets_match(
                challenge.code_hash,
                f"{job.id}:job_customer_verify:{code}",
                get_settings().secret_key,
            ):
                challenge.attempt_count += 1
                failure = AppError(400, "invalid_customer_code", "Wrong customer code.")
            else:
                challenge.consumed_at = utcnow()
    if failure is not None:
        raise failure
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
    if job.signature:
        raise AppError(409, "already_signed", "Acknowledged work cannot be changed.")
    photos = evidence.get("photo_refs") or []
    if not photos:
        raise AppError(400, "evidence_required", "At least one uploaded photo is required.")
    for key in photos:
        uploaded = db.scalar(
            select(InstallationEvidence).where(
                InstallationEvidence.job_id == job.id, InstallationEvidence.storage_key == key
            )
        )
        if uploaded is None:
            raise AppError(422, "invalid_evidence", "Every photo must be uploaded to this job.")
        verify_file(uploaded)
    job.evidence = evidence
    add_audit(
        db,
        actor_user_id=user.id,
        action="job.evidence_recorded",
        entity_type="installation_job",
        entity_id=job.id,
        metadata={"photo_count": len(photos)},
    )
    db.flush()
    return job


def verify_file(uploaded):
    payload = evidence_file(get_settings(), uploaded.storage_key).read_bytes()
    if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), uploaded.sha256):
        raise AppError(409, "evidence_modified", "Stored evidence failed its integrity check.")


def work_summary(db: Session, user: User, job_id: uuid.UUID) -> dict:
    job = get_job(db, user, job_id)
    if not job.evidence:
        raise AppError(409, "evidence_required", "Record work evidence first.")
    files = list(
        db.scalars(
            select(InstallationEvidence)
            .where(InstallationEvidence.job_id == job.id)
            .order_by(InstallationEvidence.storage_key)
        )
    )
    selected = [row for row in files if row.storage_key in job.evidence.get("photo_refs", [])]
    if len(selected) != len(set(job.evidence.get("photo_refs", []))):
        raise AppError(409, "invalid_evidence", "Recorded photos have no upload custody record.")
    for row in selected:
        verify_file(row)
    if job.status == "completed":
        acceptance = dict(job.signature or {})
        payload_hmac = acceptance.pop("payload_hmac", "")
        recorded = acceptance.get("summary")
        digest = hashlib.sha256(
            json.dumps(recorded, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if (
            not secrets_match(
                payload_hmac,
                json.dumps(acceptance, sort_keys=True, separators=(",", ":")),
                get_settings().secret_key,
            )
            or digest != acceptance.get("summary_hash")
            or not recorded
            or recorded.get("files")
            != [{"key": row.storage_key, "sha256": row.sha256} for row in selected]
        ):
            raise AppError(409, "acceptance_invalid", "Completed acknowledgment integrity failed.")
        return {"summary": recorded, "summary_hash": digest}
    arrival = job.arrival_at.astimezone(UTC).isoformat() if job.arrival_at else None
    if job.signature and job.signature.get("summary_version", 1) == 1:
        historical = job.signature.get("summary", {}).get("arrival_at")
        try:
            if (
                historical
                and job.arrival_at
                and datetime.fromisoformat(historical) == job.arrival_at
            ):
                arrival = historical
        except (ValueError, TypeError):
            pass  # Modified/malformed historical evidence must fail its hash.
    summary = {
        "job_id": str(job.id),
        "order_id": str(job.order_id),
        "technician_user_id": str(job.technician_user_id),
        "arrival_at": arrival,
        "evidence": job.evidence,
        "files": [{"key": row.storage_key, "sha256": row.sha256} for row in selected],
    }
    # Preserve signed v1 summaries. New acknowledgments explicitly bind the
    # actual unit identities too, so equipment cannot be swapped after signing.
    if not job.signature or job.signature.get("summary_version") == 2:
        summary["equipment"] = [
            {
                "id": str(row.id),
                "serial_number": row.serial_number,
                "component_code": row.component_code,
            }
            for row in db.scalars(
                select(EquipmentSerial)
                .where(EquipmentSerial.order_id == job.order_id)
                .order_by(EquipmentSerial.serial_number)
            )
        ]
    digest = hashlib.sha256(
        json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"summary": summary, "summary_hash": digest}


def record_signature(
    db: Session, user: User, job_id: uuid.UUID, signature: dict
) -> InstallationJob:
    job = db.scalar(select(InstallationJob).where(InstallationJob.id == job_id).with_for_update())
    order = db.get(SalesOrder, job.order_id) if job else None
    if not job or not order or user.role_code != "customer" or order.customer_user_id != user.id:
        raise AppError(
            403, "forbidden", "Only the owning authenticated customer may acknowledge work."
        )
    if job.signature or job.status in {"completed", "cancelled"}:
        raise AppError(409, "already_signed", "This acknowledgment cannot be replayed or replaced.")
    if not signature.get("customer_confirmed"):
        raise AppError(400, "signature_unconfirmed", "Customer confirmation is required.")
    summary = work_summary(db, user, job.id)
    if signature.get("summary_hash") != summary["summary_hash"]:
        raise AppError(
            409, "summary_changed", "Review the current work summary before acknowledging."
        )
    acceptance = {
        **signature,
        "summary_version": 2,
        "customer_user_id": str(user.id),
        "job_id": str(job.id),
        "accepted_at": utcnow().isoformat(),
        "summary": summary["summary"],
    }
    acceptance["payload_hmac"] = hash_secret(
        json.dumps(acceptance, sort_keys=True, separators=(",", ":")), get_settings().secret_key
    )
    job.signature = acceptance
    add_audit(
        db,
        actor_user_id=user.id,
        action="job.customer_acknowledged",
        entity_type="installation_job",
        entity_id=job.id,
        metadata={
            "summary_hash": summary["summary_hash"],
            "payload_hmac": acceptance["payload_hmac"],
        },
    )
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
    if job.status != "on_site" or job.arrival_at is None:
        raise AppError(409, "arrival_required", "Record arrival before completing this job.")
    summary = work_summary(db, user, job.id)
    acceptance = dict(job.signature)
    payload_hmac = acceptance.pop("payload_hmac", "")
    if (
        not secrets_match(
            payload_hmac,
            json.dumps(acceptance, sort_keys=True, separators=(",", ":")),
            get_settings().secret_key,
        )
        or acceptance.get("summary_hash") != summary["summary_hash"]
    ):
        raise AppError(409, "acceptance_invalid", "Customer acknowledgment integrity failed.")
    from app.services.serial_custody import require_order_delivered

    db.scalar(select(SalesOrder.id).where(SalesOrder.id == job.order_id).with_for_update())
    require_order_delivered(db, job.order_id)
    job.status = "completed"
    job.completed_at = utcnow()
    for unit in db.scalars(
        select(EquipmentSerial)
        .where(EquipmentSerial.order_id == job.order_id, EquipmentSerial.status == "delivered")
        .with_for_update()
    ):
        unit.status = "installed"
    from app.services.coverage_service import activate

    activate(db, user, job.order_id, "installation", job.completed_at)
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
        orders = set(
            db.scalars(select(SalesOrder.id).where(SalesOrder.customer_user_id == user.id)).all()
        )
        if not orders:
            return []
        return list(db.scalars(query.where(InstallationJob.order_id.in_(orders))))
    raise AppError(403, "forbidden", "You cannot list jobs.")
