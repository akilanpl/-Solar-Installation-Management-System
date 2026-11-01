"""Phase 4B approved estimates and immutable service billing."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.identity import User
from app.models.warranty import ServiceCreditNote, ServiceEstimate, ServiceInvoice
from app.schemas import parse_idempotency_key
from app.schemas.billing import (
    CreditNoteCreate,
    CreditNoteResponse,
    EstimateDecisionCreate,
    EstimateResponse,
    InvoiceCreate,
    InvoiceResponse,
    PriceBookCreate,
    PriceBookResponse,
    TaxPolicyCreate,
    TaxPolicyResponse,
)
from app.services import billing_service

router = APIRouter(tags=["billing"])


def _key(value: str | None) -> str:
    try:
        return parse_idempotency_key(value)
    except ValueError as exc:
        raise AppError(400, "idempotency_key_required", str(exc)) from exc


def _estimate_response(estimate: ServiceEstimate) -> EstimateResponse:
    return EstimateResponse(
        id=estimate.id, reference=estimate.reference, ticket_id=estimate.ticket_id,
        repair_job_id=estimate.repair_job_id,
        coverage_decision_id=estimate.coverage_decision_id, version=estimate.version,
        lines=estimate.lines, parts_minor=estimate.parts_minor,
        labour_minor=estimate.labour_minor, tax_minor=estimate.tax_minor,
        covered_minor=estimate.covered_minor,
        customer_payable_minor=estimate.customer_payable_minor,
        price_book_version=estimate.price_book_version,
        tax_policy_version=estimate.tax_policy_version, status=estimate.status,
        valid_until=estimate.valid_until, created_at=estimate.created_at)


def _invoice_response(invoice: ServiceInvoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id, reference=invoice.reference, estimate_id=invoice.estimate_id,
        estimate_version=invoice.estimate_version, ticket_id=invoice.ticket_id,
        lines=invoice.lines, parts_minor=invoice.parts_minor,
        labour_minor=invoice.labour_minor, tax_minor=invoice.tax_minor,
        covered_minor=invoice.covered_minor,
        customer_payable_minor=invoice.customer_payable_minor,
        credited_minor=invoice.credited_minor,
        consumption_operation_id=invoice.consumption_operation_id,
        status=invoice.status, created_at=invoice.created_at)


def _credit_response(note: ServiceCreditNote) -> CreditNoteResponse:
    return CreditNoteResponse(
        id=note.id, reference=note.reference, invoice_id=note.invoice_id,
        amount_minor=note.amount_minor, reason=note.reason, created_at=note.created_at)


@router.post("/service-price-books", response_model=PriceBookResponse, status_code=201)
def create_price_book(payload: PriceBookCreate, user: User = Depends(current_user),
                      db: Session = Depends(get_db, scope="function")):
    book = billing_service.create_price_book(
        db, user, payload.label, payload.labour_rates, payload.part_prices,
        payload.effective_from)
    return PriceBookResponse(
        version=book.version, label=book.label, labour_rates=book.labour_rates,
        part_prices=book.part_prices, effective_from=book.effective_from,
        created_at=book.created_at)


@router.get("/service-price-books", response_model=list[PriceBookResponse])
def list_price_books(user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    from app.models.warranty import ServicePriceBook

    billing_service.require_support(user)
    books = db.query(ServicePriceBook).order_by(ServicePriceBook.version.desc()).all()
    return [PriceBookResponse(
        version=book.version, label=book.label, labour_rates=book.labour_rates,
        part_prices=book.part_prices, effective_from=book.effective_from,
        created_at=book.created_at) for book in books]


@router.post("/service-tax-policies", response_model=TaxPolicyResponse, status_code=201)
def create_tax_policy(payload: TaxPolicyCreate, user: User = Depends(current_user),
                      db: Session = Depends(get_db, scope="function")):
    policy = billing_service.create_tax_policy(
        db, user, payload.label, payload.rate_bps, payload.effective_from)
    return TaxPolicyResponse(
        version=policy.version, label=policy.label, rate_bps=policy.rate_bps,
        effective_from=policy.effective_from, created_at=policy.created_at)


@router.get("/service-tax-policies", response_model=list[TaxPolicyResponse])
def list_tax_policies(user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    from app.models.warranty import ServiceTaxPolicy

    billing_service.require_support(user)
    policies = db.query(ServiceTaxPolicy).order_by(ServiceTaxPolicy.version.desc()).all()
    return [TaxPolicyResponse(
        version=policy.version, label=policy.label, rate_bps=policy.rate_bps,
        effective_from=policy.effective_from, created_at=policy.created_at)
        for policy in policies]


@router.post("/tickets/{ticket_id}/estimates", response_model=EstimateResponse,
             status_code=201)
def create_estimate(ticket_id: UUID, response: Response,
                    user: User = Depends(current_user), db: Session = Depends(get_db, scope="function"),
                    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    estimate, created = billing_service.build_estimate(db, user, ticket_id, _key(idempotency_key))
    if not created:
        response.status_code = 200
    return _estimate_response(estimate)


@router.get("/tickets/{ticket_id}/estimates", response_model=list[EstimateResponse])
def list_estimates(ticket_id: UUID, user: User = Depends(current_user),
                   db: Session = Depends(get_db, scope="function")):
    return [_estimate_response(estimate) for estimate in
            billing_service.ticket_estimates(db, user, ticket_id)]


@router.get("/estimates/{estimate_id}", response_model=EstimateResponse)
def read_estimate(estimate_id: UUID, user: User = Depends(current_user),
                  db: Session = Depends(get_db, scope="function")):
    from app.models.warranty import ServiceEstimate

    estimate = db.get(ServiceEstimate, estimate_id)
    if estimate is None:
        raise AppError(404, "not_found", "Estimate not found.")
    billing_service.ticket_estimates(db, user, estimate.ticket_id)
    return _estimate_response(estimate)


@router.post("/estimates/{estimate_id}/decision", response_model=EstimateResponse)
def decide_estimate(estimate_id: UUID, payload: EstimateDecisionCreate,
                    user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _estimate_response(billing_service.decide_estimate(
        db, user, estimate_id, payload.decision, payload.estimate_version, payload.note))


@router.post("/service-invoices", response_model=InvoiceResponse, status_code=201)
def create_invoice(payload: InvoiceCreate, response: Response,
                   user: User = Depends(current_user), db: Session = Depends(get_db, scope="function"),
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    invoice, created = billing_service.create_invoice(
        db, user, payload.estimate_id, _key(idempotency_key))
    if not created:
        response.status_code = 200
    return _invoice_response(invoice)


@router.get("/service-invoices", response_model=list[InvoiceResponse])
def list_invoices(ticket_id: UUID | None = Query(default=None),
                  user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return [_invoice_response(invoice) for invoice in
            billing_service.list_invoices(db, user, ticket_id)]


@router.get("/service-invoices/{invoice_id}", response_model=InvoiceResponse)
def read_invoice(invoice_id: UUID, user: User = Depends(current_user),
                 db: Session = Depends(get_db, scope="function")):
    return _invoice_response(billing_service.get_invoice(db, user, invoice_id))


@router.post("/service-invoices/{invoice_id}/consume", response_model=InvoiceResponse)
def consume_parts(invoice_id: UUID, user: User = Depends(current_user),
                  db: Session = Depends(get_db, scope="function")):
    return _invoice_response(billing_service.consume_invoice_parts(db, user, invoice_id))


@router.post("/service-invoices/{invoice_id}/credit-notes",
             response_model=CreditNoteResponse, status_code=201)
def create_credit_note(invoice_id: UUID, payload: CreditNoteCreate,
                       user: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return _credit_response(billing_service.create_credit_note(
        db, user, invoice_id, payload.amount_minor, payload.reason))


@router.get("/service-invoices/{invoice_id}/credit-notes",
            response_model=list[CreditNoteResponse])
def list_credit_notes(invoice_id: UUID, user: User = Depends(current_user),
                      db: Session = Depends(get_db, scope="function")):
    invoice = billing_service.get_invoice(db, user, invoice_id)
    notes = billing_service.invoice_credit_notes(db, user, invoice.id)
    return [_credit_response(note) for note in notes]
