"""Phase 4E offline-first intake for technicians.

The browser keeps drafts in IndexedDB and replays them here. Every verdict
is durable: duplicates return the stored result, stale versions conflict,
and forbidden actions are rejected with no state change.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_limiter, get_settings
from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.db.session import get_db as get_db_dep
from app.models.identity import User
from app.schemas import (
    OfflineAssignmentResponse,
    SyncBatchRequest,
    SyncBatchResponse,
    SyncOperationRecord,
    SyncVerdictResponse,
)
from app.services import offline_sync_service

router = APIRouter(prefix="/offline", tags=["offline-4e"])


@router.post("/sync", response_model=SyncBatchResponse)
def sync_batch(
    payload: SyncBatchRequest,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> SyncBatchResponse:
    limiter.check(
        f"offline-sync:{user.id}", limit=30, window_seconds=settings.rate_limit_window_seconds
    )
    verdicts = offline_sync_service.submit_batch(
        db, settings, user, [entry.model_dump() for entry in payload.operations]
    )
    return SyncBatchResponse(
        verdicts=[SyncVerdictResponse(**verdict) for verdict in verdicts]
    )


@router.post("/evidence", response_model=SyncVerdictResponse, status_code=201)
def upload_evidence(
    request: Request,
    client_operation_id: str = Form(...),
    target: str = Form(...),
    entity_id: uuid.UUID = Form(...),
    upload: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_limiter),
) -> SyncVerdictResponse:
    limiter.check(
        f"offline-evidence:{user.id}", limit=30,
        window_seconds=settings.rate_limit_window_seconds,
    )
    payload = upload.file.read(settings.evidence_max_bytes + 1)
    result = offline_sync_service.upload_evidence(
        db, settings, user,
        client_operation_id=client_operation_id,
        target=target,
        entity_id=entity_id,
        filename=upload.filename or "evidence",
        payload=payload,
    )
    return SyncVerdictResponse(
        client_operation_id=client_operation_id,
        operation_id=None,
        op_type="evidence_intent",
        status="applied",
        result=result,
        duplicate=result.get("duplicate", False),
    )


@router.get("/operations", response_model=list[SyncOperationRecord])
def list_operations(
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
) -> list[SyncOperationRecord]:
    return [
        SyncOperationRecord(**item)
        for item in offline_sync_service.recent_operations(db, user)
    ]


@router.get("/assignments", response_model=OfflineAssignmentResponse)
def offline_assignments(
    user: User = Depends(current_user),
    db: Session = Depends(get_db_dep, scope="function"),
) -> OfflineAssignmentResponse:
    return OfflineAssignmentResponse(
        **offline_sync_service.offline_assignments(db, user)
    )
