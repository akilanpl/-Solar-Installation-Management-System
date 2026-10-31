from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_settings
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.workflow import Survey
from app.schemas.workflow import (
    EvidenceResponse,
    SurveyAssignment,
    SurveyCreate,
    SurveyDecision,
    SurveyHistoryResponse,
    SurveyList,
    SurveyResponse,
    SurveySubmit,
)
from app.services import survey_service
from app.services.evidence_store import evidence_file, save_evidence

router = APIRouter(prefix="/surveys", tags=["surveys"])


def survey_response(survey: Survey) -> SurveyResponse:
    return SurveyResponse(
        id=survey.id,
        reference=survey.reference,
        enquiry_id=survey.enquiry_id,
        customer_user_id=survey.customer_user_id,
        site_id=survey.site_id,
        assigned_technician_user_id=survey.assigned_technician_user_id,
        appointment_status=survey.appointment_status,
        appointment_starts_at=survey.appointment_starts_at,
        status=survey.status,
        revision_number=survey.revision_number,
        revision_of_survey_id=survey.revision_of_survey_id,
        azimuth_deg=survey.azimuth_deg,
        tilt_deg=survey.tilt_deg,
        shadow_free_area_sqm=survey.shadow_free_area_sqm,
        cable_distance_m=survey.cable_distance_m,
        grid_connection=survey.grid_connection,
        notes=survey.notes,
        submitted_at=survey.submitted_at,
        reviewed_at=survey.reviewed_at,
        reviewed_by_user_id=survey.reviewed_by_user_id,
        evidence=[
            EvidenceResponse(
                id=item.id,
                content_type=item.content_type,
                size_bytes=item.size_bytes,
                original_filename=item.original_filename,
                created_at=item.created_at,
            )
            for item in survey.evidence
        ],
        history=[
            SurveyHistoryResponse(
                id=item.id,
                from_status=item.from_status,
                to_status=item.to_status,
                note=item.note,
                created_at=item.created_at,
            )
            for item in survey.history
        ],
        created_at=survey.created_at,
        updated_at=survey.updated_at,
    )


@router.post("", response_model=SurveyResponse, status_code=201)
def create_survey(
    payload: SurveyCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> SurveyResponse:
    return survey_response(survey_service.create_survey(db, user, payload.enquiry_id))


@router.get("", response_model=SurveyList)
def list_surveys(
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SurveyList:
    rows, total = survey_service.list_surveys(db, user, page=page, page_size=page_size)
    return SurveyList(
        items=[survey_response(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{survey_id}", response_model=SurveyResponse)
def read_survey(
    survey_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> SurveyResponse:
    return survey_response(survey_service.get_survey(db, user, survey_id))


@router.post("/{survey_id}/assignment", response_model=SurveyResponse)
def assign_survey(
    survey_id: UUID,
    payload: SurveyAssignment,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> SurveyResponse:
    return survey_response(survey_service.assign_survey(db, user, survey_id, payload))


@router.post("/{survey_id}/start", response_model=SurveyResponse)
def start_survey(
    survey_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> SurveyResponse:
    return survey_response(survey_service.start_survey(db, user, survey_id))


@router.post("/{survey_id}/submission", response_model=SurveyResponse)
def submit_survey(
    survey_id: UUID,
    payload: SurveySubmit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> SurveyResponse:
    return survey_response(survey_service.submit_survey(db, user, survey_id, payload))


@router.post("/{survey_id}/approval", response_model=SurveyResponse)
def decide_survey(
    survey_id: UUID,
    payload: SurveyDecision,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> SurveyResponse:
    return survey_response(survey_service.decide_survey(db, user, survey_id, payload))


@router.post("/{survey_id}/resurvey", response_model=SurveyResponse, status_code=201)
def resurvey(
    survey_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> SurveyResponse:
    return survey_response(survey_service.resurvey(db, user, survey_id))


@router.post("/{survey_id}/evidence", response_model=EvidenceResponse, status_code=201)
def upload_evidence(
    survey_id: UUID,
    upload: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
) -> EvidenceResponse:
    payload = upload.file.read(settings.evidence_max_bytes + 1)
    key, content_type = save_evidence(settings, payload)
    try:
        row = survey_service.add_evidence(
            db,
            user,
            survey_id,
            storage_key=key,
            content_type=content_type,
            size_bytes=len(payload),
            original_filename=upload.filename or "evidence",
        )
    except AppError:
        evidence_file(settings, key).unlink(missing_ok=True)
        raise
    return EvidenceResponse(
        id=row.id,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        original_filename=row.original_filename,
        created_at=row.created_at,
    )


@router.get("/{survey_id}/evidence/{evidence_id}")
def download_evidence(
    survey_id: UUID,
    evidence_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    survey = survey_service.get_survey(db, user, survey_id)
    match = next((item for item in survey.evidence if item.id == evidence_id), None)
    if match is None:
        raise AppError(404, "not_found", "Evidence not found.")
    return FileResponse(evidence_file(settings, match.storage_key), media_type=match.content_type)
