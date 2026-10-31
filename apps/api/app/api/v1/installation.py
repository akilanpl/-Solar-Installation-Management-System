import hashlib
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.phase3 import InstallationEvidence
from app.models.workflow import SalesOrder
from app.schemas.phase3 import (
    InstallationUploadResponse,
    JobCreate,
    JobEvidence,
    JobOtpVerify,
    JobResponse,
    JobSignature,
    RecommendationRequest,
    RecommendationResponse,
    SchedulingSlotUpdate,
    WarrantyResponse,
    WorkSummaryResponse,
)
from app.services import fulfillment_service, installation_service
from app.services.email_sender import OutboundEmail
from app.services.evidence_store import evidence_file, save_evidence

router = APIRouter(tags=["installation"])


def _job_payload(job, customer_code: str | None = None) -> JobResponse:
    return JobResponse(
        id=job.id,
        reference=job.reference,
        order_id=job.order_id,
        scheduling_request_id=job.scheduling_request_id,
        technician_user_id=job.technician_user_id,
        status=job.status,
        slot_starts_at=job.slot_starts_at,
        arrival_at=job.arrival_at,
        otp_verified=job.otp_verified,
        evidence=job.evidence,
        signature=job.signature,
        completed_at=job.completed_at,
        customer_code=customer_code,
        created_at=job.created_at,
    )


@router.post("/scheduling/installations/{scheduling_id}/slot")
def schedule_slot(
    scheduling_id: UUID,
    payload: SchedulingSlotUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = installation_service.schedule_slot(db, user, scheduling_id, payload.slot_starts_at)
    return {
        "id": row.id,
        "status": row.status,
        "slot_starts_at": row.slot_starts_at,
    }


@router.post("/assignments/recommendations", response_model=list[RecommendationResponse])
def recommend(
    payload: RecommendationRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return [
        RecommendationResponse(
            technician_user_id=item["technician_user_id"],
            employee_code=item["employee_code"],
            open_jobs=item["open_jobs"],
            reason=item["reason"],
        )
        for item in installation_service.recommend_technicians(
            db, user, payload.order_id, payload.max_results
        )
    ]


@router.post("/jobs", response_model=JobResponse)
def create_job(
    payload: JobCreate,
    response: Response,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    job, code = installation_service.create_job(
        db, user, payload.order_id, payload.technician_user_id, payload.slot_starts_at
    )
    response.status_code = 201
    order = db.get(SalesOrder, job.order_id)
    customer = db.get(User, order.customer_user_id)
    request.app.state.email_sender.send(OutboundEmail(
        recipient=customer.email, subject=f"SolarOps installation {job.reference}",
        body=f"Installation {job.reference}: your verification code is {code}. Share it only for this job. This is not work acceptance.", code=code))
    return _job_payload(job)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [_job_payload(job) for job in installation_service.list_jobs(db, user)]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def read_job(job_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _job_payload(installation_service.get_job(db, user, job_id))


@router.post("/jobs/{job_id}/en-route", response_model=JobResponse)
def job_en_route(job_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _job_payload(installation_service.mark_en_route(db, user, job_id))


@router.post("/jobs/{job_id}/arrival", response_model=JobResponse)
def job_arrival(job_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _job_payload(installation_service.mark_arrival(db, user, job_id))


@router.post("/jobs/{job_id}/customer-otp", response_model=JobResponse)
def job_otp(
    job_id: UUID,
    payload: JobOtpVerify,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _job_payload(installation_service.verify_customer_otp(db, user, job_id, payload.code))


@router.post("/jobs/{job_id}/evidence", response_model=JobResponse)
def job_evidence(
    job_id: UUID,
    payload: JobEvidence,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _job_payload(
        installation_service.record_evidence(db, user, job_id, payload.model_dump(mode="json"))
    )


@router.post("/jobs/{job_id}/signature", response_model=JobResponse)
def job_signature(
    job_id: UUID,
    payload: JobSignature,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _job_payload(
        installation_service.record_signature(db, user, job_id, payload.model_dump())
    )


@router.post("/jobs/{job_id}/completion", response_model=JobResponse)
def job_completion(job_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _job_payload(installation_service.complete_job(db, user, job_id))


@router.get("/warranties/order/{order_id}", response_model=WarrantyResponse)
def read_warranty(
    order_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = fulfillment_service.get_warranty(db, user, order_id)
    return WarrantyResponse(
        id=row.id,
        order_id=row.order_id,
        status=row.status,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        coverage_note=row.coverage_note,
    )


@router.post("/warranties/order/{order_id}/void", response_model=WarrantyResponse)
def void_warranty(
    order_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    row = fulfillment_service.void_warranty(db, user, order_id)
    return WarrantyResponse(
        id=row.id,
        order_id=row.order_id,
        status=row.status,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        coverage_note=row.coverage_note,
    )


@router.get("/jobs/{job_id}/work-summary", response_model=WorkSummaryResponse)
def work_summary(job_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return installation_service.work_summary(db, user, job_id)


@router.post("/jobs/{job_id}/uploads", status_code=201, response_model=InstallationUploadResponse)
def upload_job_evidence(job_id: UUID, request: Request, upload: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = installation_service._job_for_technician(db, user, job_id)
    if user.role_code != "technician" or job.technician_user_id != user.id:
        raise AppError(403, "forbidden", "Only the assigned technician may upload installation evidence.")
    if job.signature or job.status in {"completed", "cancelled"}:
        raise AppError(409, "invalid_transition", "Evidence is closed for this job.")
    settings = request.app.state.settings
    payload = upload.file.read(settings.evidence_max_bytes + 1)
    if len(payload) > settings.evidence_max_bytes:
        raise AppError(413, "file_too_large", "Installation photo exceeds the upload limit.")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"} or image.width * image.height > 25_000_000:
                raise ValueError("Unsupported image or excessive dimensions")
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise AppError(422, "invalid_evidence", "Upload a valid JPEG, PNG, or WebP photo.") from exc
    key, content_type = save_evidence(settings, payload)
    if not content_type.startswith("image/"):
        evidence_file(settings, key).unlink(missing_ok=True)
        raise AppError(422, "invalid_evidence", "Installation photos must be images.")
    row = InstallationEvidence(job_id=job.id, uploaded_by_user_id=user.id, storage_key=key,
        content_type=content_type, size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    db.add(row)
    db.flush()
    return {"storage_key": key, "sha256": row.sha256, "uploaded_at": row.created_at}


@router.get("/jobs/{job_id}/uploads/{storage_key}")
def download_job_evidence(job_id: UUID, storage_key: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    installation_service.get_job(db, user, job_id)
    row = db.scalar(select(InstallationEvidence).where(InstallationEvidence.job_id == job_id, InstallationEvidence.storage_key == storage_key))
    if row is None:
        raise AppError(404, "not_found", "Evidence not found.")
    installation_service.verify_file(row)
    return FileResponse(evidence_file(installation_service.get_settings(), row.storage_key), media_type=row.content_type, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/jobs/{job_id}/verification-code/request")
def request_verification_code(job_id: UUID, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Reissue through the owning customer's configured email channel only."""
    import secrets
    from datetime import timedelta

    from app.core.security import hash_secret, utcnow
    from app.models.phase3 import InstallationJob, InstallationOtp
    from app.repositories.queries import add_audit

    visible = installation_service.get_job(db, user, job_id)
    order = db.get(SalesOrder, visible.order_id)
    if user.role_code != "customer" or order.customer_user_id != user.id:
        raise AppError(403, "forbidden", "Only the owning customer may request a verification code.")
    job = db.scalar(select(InstallationJob).where(InstallationJob.id == job_id).with_for_update())
    if job.otp_verified or job.status in {"cancelled", "completed"}:
        raise AppError(409, "invalid_transition", "This job does not need a new verification code.")
    recent = db.scalar(select(InstallationOtp).where(InstallationOtp.job_id == job_id).order_by(InstallationOtp.created_at.desc()).limit(1))
    if recent and recent.created_at > utcnow() - timedelta(minutes=1):
        raise AppError(429, "rate_limited", "Wait one minute before requesting a new code.")
    active = db.scalars(select(InstallationOtp).where(InstallationOtp.job_id == job_id, InstallationOtp.consumed_at.is_(None)).with_for_update())
    for challenge in active:
        challenge.consumed_at = utcnow()
    code = f"{secrets.randbelow(900000) + 100000:06d}"
    settings = request.app.state.settings
    db.add(InstallationOtp(job_id=job.id, purpose="job_customer_verify", code_hash=hash_secret(f"{job.id}:job_customer_verify:{code}", settings.secret_key), expires_at=utcnow() + timedelta(minutes=30)))
    request.app.state.email_sender.send(OutboundEmail(recipient=user.email, subject=f"SolarOps installation {job.reference}", body=f"Installation {job.reference}: verification code {code}. This does not acknowledge completed work.", code=code))
    add_audit(db, actor_user_id=user.id, action="job.verification_code_requested", entity_type="installation_job", entity_id=job.id, metadata={"channel": "configured_customer_email"})
    db.flush()
    return {"message": "Verification code submitted to your configured email channel. Delivery is not confirmed."}
