from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_settings
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.workflow import Quotation
from app.schemas import parse_idempotency_key
from app.schemas.workflow import (
    QuotationCreate,
    QuotationLineResponse,
    QuotationList,
    QuotationResponse,
    QuotationRevisionCreate,
    RevisionRequestCreate,
    RevisionRequestResponse,
)
from app.services import quotation_service

router = APIRouter(prefix="/quotations", tags=["quotations"])


def quotation_response(db: Session, quotation: Quotation) -> QuotationResponse:
    return QuotationResponse(
        id=quotation.id,
        reference=quotation.reference,
        enquiry_id=quotation.enquiry_id,
        survey_id=quotation.survey_id,
        customer_user_id=quotation.customer_user_id,
        site_id=quotation.site_id,
        package_code=quotation_service.package_code(db, quotation),
        template_version_id=quotation.template_version_id,
        version_number=quotation.version_number,
        supersedes_quotation_id=quotation.supersedes_quotation_id,
        status=quotation.status,
        material_cost_minor=quotation.material_cost_minor,
        material_total_minor=quotation.material_total_minor,
        installation_total_minor=quotation.installation_total_minor,
        discount_minor=quotation.discount_minor,
        tax_minor=quotation.tax_minor,
        tax_rate_bps=quotation.tax_rate_bps,
        total_minor=quotation.total_minor,
        currency_code=quotation.currency_code,
        expires_at=quotation.expires_at,
        issued_at=quotation.issued_at,
        lines=[
            QuotationLineResponse(
                component_code=line.component_code,
                description=line.description,
                line_kind=line.line_kind,
                quantity=line.quantity,
                unit=line.unit,
                unit_cost_minor=line.unit_cost_minor,
                unit_price_minor=line.unit_price_minor,
                line_total_minor=line.line_total_minor,
                sort_order=line.sort_order,
            )
            for line in quotation.lines
        ],
    )


def _key(value: str | None) -> str:
    try:
        return parse_idempotency_key(value)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc


@router.post("", response_model=QuotationResponse)
def create_quotation(
    payload: QuotationCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> QuotationResponse:
    quotation, replayed = quotation_service.create_quotation(
        db, settings, user, payload, _key(idempotency_key)
    )
    response.status_code = 200 if replayed else 201
    return quotation_response(db, quotation)


@router.get("", response_model=QuotationList)
def list_quotations(
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> QuotationList:
    rows, total = quotation_service.list_quotations(db, user, page=page, page_size=page_size)
    return QuotationList(
        items=[quotation_response(db, row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{quotation_id}", response_model=QuotationResponse)
def read_quotation(
    quotation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> QuotationResponse:
    return quotation_response(db, quotation_service.get_quotation(db, user, quotation_id))


@router.post("/{quotation_id}/revisions", response_model=QuotationResponse)
def revise_quotation(
    quotation_id: UUID,
    payload: QuotationRevisionCreate,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
    settings: Settings = Depends(get_settings),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> QuotationResponse:
    quotation, replayed = quotation_service.revise_quotation(
        db, settings, user, quotation_id, payload, _key(idempotency_key)
    )
    response.status_code = 200 if replayed else 201
    return quotation_response(db, quotation)


@router.post(
    "/{quotation_id}/revision-requests", response_model=RevisionRequestResponse, status_code=201
)
def request_revision(
    quotation_id: UUID,
    payload: RevisionRequestCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> RevisionRequestResponse:
    row = quotation_service.request_revision(db, user, quotation_id, payload)
    return RevisionRequestResponse(
        id=row.id,
        quotation_id=row.quotation_id,
        category=row.category,
        request_text=row.request_text,
        status=row.status,
        created_at=row.created_at,
    )


@router.get("/{quotation_id}/revision-requests", response_model=list[RevisionRequestResponse])
def list_revision_requests(
    quotation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> list[RevisionRequestResponse]:
    return [
        RevisionRequestResponse(
            id=row.id,
            quotation_id=row.quotation_id,
            category=row.category,
            request_text=row.request_text,
            status=row.status,
            created_at=row.created_at,
        )
        for row in quotation_service.list_revision_requests(db, user, quotation_id)
    ]


@router.post("/{quotation_id}/acceptance", response_model=QuotationResponse)
def accept_quotation(
    quotation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> QuotationResponse:
    return quotation_response(db, quotation_service.accept_quotation(db, user, quotation_id))


@router.post("/{quotation_id}/withdrawal", response_model=QuotationResponse)
def withdraw_quotation(
    quotation_id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db, scope="function"),
) -> QuotationResponse:
    return quotation_response(db, quotation_service.withdraw_quotation(db, user, quotation_id))
