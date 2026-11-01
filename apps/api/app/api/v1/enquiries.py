from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.schemas import (
    EnquiryCreate,
    EnquiryDetail,
    EnquiryList,
    QualificationUpdate,
    parse_idempotency_key,
)
from app.services import enquiry_service
from app.services.presenters import detail_from, summary_from

router = APIRouter(prefix="/enquiries", tags=["enquiries"])


@router.post("", response_model=EnquiryDetail)
def create_enquiry(
    payload: EnquiryCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> EnquiryDetail:
    try:
        key = parse_idempotency_key(idempotency_key)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc
    enquiry, replayed = enquiry_service.create_enquiry(db, user, payload, key)
    response.status_code = 200 if replayed else 201
    return detail_from(enquiry)


@router.get("", response_model=EnquiryList)
def list_enquiries(
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> EnquiryList:
    rows, total = enquiry_service.list_visible_enquiries(db, user, page=page, page_size=page_size)
    return EnquiryList(
        items=[summary_from(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{enquiry_id}", response_model=EnquiryDetail)
def read_enquiry(
    enquiry_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> EnquiryDetail:
    return detail_from(enquiry_service.get_visible_enquiry(db, user, enquiry_id))


@router.patch("/{enquiry_id}/qualification", response_model=EnquiryDetail)
def qualify_enquiry(
    enquiry_id: UUID,
    payload: QualificationUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> EnquiryDetail:
    return detail_from(enquiry_service.qualify_enquiry(db, user, enquiry_id, payload))
