"""Phase 4B equipment replacement with warehouse custody."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.phase3 import EquipmentSerial
from app.models.warranty import ReplacementDecision
from app.schemas import parse_idempotency_key
from app.schemas.replacement import (
    InspectionCreate,
    InspectionResponse,
    ManufacturerAuth,
    ReplacementCreate,
    ReplacementResponse,
)
from app.schemas.support import ReasonedAction
from app.services import replacement_service

router = APIRouter(tags=["replacements"])


def _key(value: str | None) -> str:
    try:
        return parse_idempotency_key(value)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc


def _response(db: Session, row: ReplacementDecision) -> ReplacementResponse:
    old = db.get(EquipmentSerial, row.old_serial_id)
    new = db.get(EquipmentSerial, row.new_serial_id)
    return ReplacementResponse(
        id=row.id, reference=row.reference, ticket_id=row.ticket_id,
        old_serial_number=old.serial_number if old else "",
        new_serial_number=new.serial_number if new else "",
        status=row.status, manufacturer_status=row.manufacturer_status,
        issue_operation_id=row.issue_operation_id,
        approved_by_user_id=row.approved_by_user_id, created_at=row.created_at)


@router.post("/replacements", response_model=ReplacementResponse, status_code=201)
def propose(payload: ReplacementCreate, response: Response,
            user: User = Depends(current_user), db: Session = Depends(get_db, scope="function"),
            idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    row, created = replacement_service.propose_replacement(
        db, user, payload.ticket_id, payload.old_serial_number, payload.new_serial_number,
        _key(idempotency_key))
    if not created:
        response.status_code = 200
    return _response(db, row)


@router.get("/replacements", response_model=list[ReplacementResponse])
def list_all(ticket_id: UUID | None = Query(default=None),
             user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return [_response(db, row) for row in
            replacement_service.list_replacements(db, user, ticket_id)]


@router.get("/replacements/{replacement_id}", response_model=ReplacementResponse)
def read_one(replacement_id: UUID, user: User = Depends(current_user),
             db: Session = Depends(get_db, scope="function")):
    return _response(db, replacement_service.get_replacement(db, user, replacement_id))


@router.post("/replacements/{replacement_id}/approve", response_model=ReplacementResponse)
def approve(replacement_id: UUID, user: User = Depends(current_user),
            db: Session = Depends(get_db, scope="function")):
    return _response(db, replacement_service.approve_replacement(db, user, replacement_id))


@router.post("/replacements/{replacement_id}/manufacturer-auth",
             response_model=ReplacementResponse)
def manufacturer_auth(replacement_id: UUID, payload: ManufacturerAuth,
                      user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _response(db, replacement_service.record_manufacturer_auth(
        db, user, replacement_id, payload.evidence_ref))


@router.post("/replacements/{replacement_id}/reserve", response_model=ReplacementResponse)
def reserve(replacement_id: UUID, user: User = Depends(current_user),
            db: Session = Depends(get_db, scope="function")):
    return _response(db, replacement_service.reserve_replacement(db, user, replacement_id))


@router.post("/replacements/{replacement_id}/issue", response_model=ReplacementResponse)
def issue(replacement_id: UUID, user: User = Depends(current_user),
          db: Session = Depends(get_db, scope="function"),
          idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _key(idempotency_key)
    return _response(db, replacement_service.issue_replacement(
        db, user, replacement_id, idempotency_key or ""))


@router.post("/replacements/{replacement_id}/install", response_model=ReplacementResponse)
def install(replacement_id: UUID, user: User = Depends(current_user),
            db: Session = Depends(get_db, scope="function")):
    return _response(db, replacement_service.confirm_install(db, user, replacement_id))


@router.post("/replacements/{replacement_id}/inspect", response_model=InspectionResponse,
             status_code=201)
def inspect_return(replacement_id: UUID, payload: InspectionCreate,
                   user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    row = replacement_service.inspect_return(
        db, user, replacement_id, payload.verdict, payload.note)
    return InspectionResponse(
        id=row.id, replacement_id=row.replacement_id, verdict=row.verdict, note=row.note,
        restock_operation_id=row.restock_operation_id, created_at=row.created_at)


@router.post("/replacements/{replacement_id}/cancel", response_model=ReplacementResponse)
def cancel(replacement_id: UUID, payload: ReasonedAction,
           user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _response(db, replacement_service.cancel_replacement(
        db, user, replacement_id, payload.reason))
