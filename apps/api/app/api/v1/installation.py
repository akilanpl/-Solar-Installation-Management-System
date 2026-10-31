from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.phase3 import (
    JobCreate,
    JobEvidence,
    JobOtpVerify,
    JobResponse,
    JobSignature,
    RecommendationRequest,
    RecommendationResponse,
    SchedulingSlotUpdate,
    WarrantyResponse,
)
from app.services import fulfillment_service, installation_service

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
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    job, code = installation_service.create_job(
        db, user, payload.order_id, payload.technician_user_id, payload.slot_starts_at
    )
    response.status_code = 201
    return _job_payload(job, customer_code=code)


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
