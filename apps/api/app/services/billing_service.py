"""Approved repair estimates and immutable service billing.

Prices are never invented here. Part prices come from the customer's own
frozen order lines first and from an admin-recorded price book second;
labour rates and tax rates come only from admin-recorded versions. Every
amount is an integer number of INR paise with documented rounding. Invoices
snapshot one accepted estimate version and stay outstanding without a real
settlement provider: no route marks an invoice paid. Credit notes adjust
without rewriting the invoice.
"""

import hashlib
import json
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import utcnow
from app.models.identity import User
from app.models.support import ServiceTicket, ServiceTicketEvent, TicketRepairJob
from app.models.warranty import (
    CoverageDecision,
    EstimateDecision,
    ServiceCreditNote,
    ServiceEstimate,
    ServiceInvoice,
    ServicePriceBook,
    ServiceTaxPolicy,
)
from app.models.workflow import SalesOrderLine
from app.repositories.queries import add_audit
from app.services import inventory_service
from app.services.references import next_reference

CUSTOMER = "customer"
SUPPORT = {"support", "admin"}
ADMIN = {"admin"}
WAREHOUSE = {"warehouse_staff", "warehouse_manager", "admin"}
LABOUR_CODE = "repair_labour"


def _digest(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_roles(user: User, allowed: set[str]) -> None:
    if user.role_code not in allowed:
        raise AppError(403, "forbidden", "You do not have access to this action.")


def require_support(user: User) -> None:
    """Visibility check for price and tax administration lists."""
    _require_roles(user, SUPPORT)


def create_price_book(db: Session, user: User, label: str, labour_rates: dict,
                      part_prices: dict, effective_from) -> ServicePriceBook:
    _require_roles(user, ADMIN)
    if len(label.strip()) < 3:
        raise AppError(422, "validation_error", "A price book needs a label.")
    for code, rate in (labour_rates or {}).items():
        if not isinstance(rate, int) or rate <= 0:
            raise AppError(422, "validation_error",
                           f"Labour rate for {code} must be positive paise per hour.")
    for code, price in (part_prices or {}).items():
        if not isinstance(price, int) or price <= 0:
            raise AppError(422, "validation_error",
                           f"Part price for {code} must be positive paise.")
    latest = db.scalar(select(func.max(ServicePriceBook.version))) or 0
    book = ServicePriceBook(
        version=latest + 1, label=label.strip(),
        labour_rates=dict(labour_rates or {}), part_prices=dict(part_prices or {}),
        effective_from=effective_from, created_by_user_id=user.id,
    )
    db.add(book)
    db.flush()
    add_audit(db, actor_user_id=user.id, action="billing.price_book_created",
              entity_type="service_price_book", entity_id=book.id,
              metadata={"version": book.version})
    db.flush()
    return book


def create_tax_policy(db: Session, user: User, label: str, rate_bps: int,
                      effective_from) -> ServiceTaxPolicy:
    _require_roles(user, ADMIN)
    if len(label.strip()) < 3:
        raise AppError(422, "validation_error", "A tax policy needs a label.")
    if not isinstance(rate_bps, int) or rate_bps < 0:
        raise AppError(422, "validation_error", "Tax rate must be non-negative basis points.")
    latest = db.scalar(select(func.max(ServiceTaxPolicy.version))) or 0
    policy = ServiceTaxPolicy(
        version=latest + 1, label=label.strip(), rate_bps=rate_bps,
        effective_from=effective_from, created_by_user_id=user.id,
    )
    db.add(policy)
    db.flush()
    add_audit(db, actor_user_id=user.id, action="billing.tax_policy_created",
              entity_type="service_tax_policy", entity_id=policy.id,
              metadata={"version": policy.version, "rate_bps": rate_bps})
    db.flush()
    return policy


def _effective_book(db: Session) -> ServicePriceBook:
    now = utcnow()
    book = db.scalar(
        select(ServicePriceBook)
        .where(ServicePriceBook.effective_from <= now)
        .order_by(ServicePriceBook.version.desc())
    )
    if book is None:
        raise AppError(409, "pricing_unavailable",
                       "No approved price book is effective. Ask an admin to record one.")
    return book


def _effective_tax(db: Session) -> ServiceTaxPolicy:
    now = utcnow()
    policy = db.scalar(
        select(ServiceTaxPolicy)
        .where(ServiceTaxPolicy.effective_from <= now)
        .order_by(ServiceTaxPolicy.version.desc())
    )
    if policy is None:
        raise AppError(409, "pricing_unavailable",
                       "No approved tax policy is effective. Ask an admin to record one.")
    return policy


def _order_part_price(db: Session, order_id: uuid.UUID, component_code: str) -> int | None:
    line = db.scalar(
        select(SalesOrderLine).where(
            SalesOrderLine.order_id == order_id,
            SalesOrderLine.component_code == component_code,
            SalesOrderLine.line_kind == "material",
        )
    )
    if line is None or line.quantity in (None, 0):
        return None
    return int(line.unit_price_minor)


def _latest_decision(db: Session, ticket_id: uuid.UUID) -> CoverageDecision:
    decision = db.scalar(
        select(CoverageDecision)
        .where(CoverageDecision.ticket_id == ticket_id)
        .order_by(CoverageDecision.created_at.desc())
    )
    if decision is None:
        raise AppError(409, "coverage_decision_required",
                       "Record a coverage decision for this ticket first.")
    return decision


def _submitted_job(db: Session, ticket_id: uuid.UUID) -> TicketRepairJob:
    job = db.scalar(
        select(TicketRepairJob)
        .where(TicketRepairJob.ticket_id == ticket_id,
               TicketRepairJob.status == "work_submitted")
        .order_by(TicketRepairJob.updated_at.desc())
    )
    if job is None:
        raise AppError(409, "work_required",
                       "The technician must submit recorded work before estimating.")
    return job


def build_estimate(db: Session, user: User, ticket_id: uuid.UUID,
                   idempotency_key: str) -> tuple[ServiceEstimate, bool]:
    _require_roles(user, SUPPORT)
    ticket = db.scalar(
        select(ServiceTicket).where(ServiceTicket.id == ticket_id).with_for_update()
    )
    if ticket is None:
        raise AppError(404, "not_found", "Ticket not found.")
    job = _submitted_job(db, ticket.id)
    decision = _latest_decision(db, ticket.id)
    if decision.verdict in ("pending_verification", "blocked"):
        raise AppError(409, "coverage_not_final",
                       "The coverage decision is not final; estimates need a verdict.")
    book = _effective_book(db)
    tax = _effective_tax(db)
    snapshot = decision.policy_snapshot or {}
    covered_components = snapshot.get("covered_components") or []
    excluded_components = (snapshot.get("exclusions") or {}).get("components") or []
    covered_verdict = decision.verdict == "covered"
    lines: list[dict] = []
    parts_minor = 0
    covered_minor = 0
    for entry in job.parts_used or []:
        code = entry.get("component_code")
        quantity = entry.get("quantity", 0)
        if not code or not isinstance(quantity, int) or quantity <= 0:
            raise AppError(422, "validation_error", "Recorded parts are malformed.")
        unit = _order_part_price(db, ticket.order_id, code)
        source = "order"
        if unit is None:
            unit = book.part_prices.get(code)
            source = "price_book"
        if unit is None:
            raise AppError(409, "pricing_unavailable",
                           f"No approved price exists for part {code}.")
        total = quantity * unit
        parts_minor += total
        covered = (covered_verdict
                   and ("*" in covered_components or code in covered_components)
                   and code not in excluded_components)
        covered_minor += total if covered else 0
        lines.append({
            "kind": "part", "code": code, "quantity": quantity, "unit": "unit",
            "unit_minor": unit, "line_total_minor": total,
            "covered_minor": total if covered else 0,
            "payable_minor": 0 if covered else total, "source": source,
            "stock_ok": bool(inventory_service.on_hand(db, code, "MAIN") >= quantity),
        })
    labour_minor = 0
    if job.work_started_at is None or job.work_finished_at is None:
        raise AppError(409, "work_required", "Recorded work has no billable time.")
    minutes = int((job.work_finished_at - job.work_started_at).total_seconds() // 60)
    if minutes < 1:
        raise AppError(409, "work_required", "Recorded work has no billable time.")
    rate = book.labour_rates.get(LABOUR_CODE)
    if rate is None:
        raise AppError(409, "pricing_unavailable",
                       "No approved labour rate is recorded for repair work.")
    labour_minor = (rate * minutes + 30) // 60
    labour_covered = covered_verdict and bool(snapshot.get("labour_covered", False))
    covered_minor += labour_minor if labour_covered else 0
    lines.append({
        "kind": "labour", "code": LABOUR_CODE, "quantity": minutes, "unit": "minute",
        "unit_minor": rate, "line_total_minor": labour_minor,
        "covered_minor": labour_minor if labour_covered else 0,
        "payable_minor": 0 if labour_covered else labour_minor,
        "source": "price_book", "stock_ok": None,
    })
    payable_subtotal = parts_minor + labour_minor - covered_minor
    tax_minor = (payable_subtotal * tax.rate_bps + 5000) // 10000
    payable = payable_subtotal + tax_minor
    digest = _digest({"ticket_id": str(ticket.id), "job_id": str(job.id),
                      "decision_id": str(decision.id), "lines": lines,
                      "book_version": book.version, "tax_version": tax.version})
    existing = db.scalar(
        select(ServiceEstimate).where(
            ServiceEstimate.ticket_id == ticket.id,
            ServiceEstimate.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != digest:
            raise AppError(409, "idempotency_conflict",
                           "This Idempotency-Key was already used for a different estimate.")
        return existing, False
    latest_version = db.scalar(
        select(func.max(ServiceEstimate.version)).where(
            ServiceEstimate.ticket_id == ticket.id)
    ) or 0
    superseded = list(
        db.scalars(
            select(ServiceEstimate).where(
                ServiceEstimate.ticket_id == ticket.id,
                ServiceEstimate.status.in_(("proposed", "rejected")),
            )
        ).all()
    )
    for old in superseded:
        old.status = "superseded"
    estimate = ServiceEstimate(
        reference=next_reference(db, "estimate", "EST"),
        ticket_id=ticket.id, repair_job_id=job.id, coverage_decision_id=decision.id,
        version=latest_version + 1, lines=lines,
        parts_minor=parts_minor, labour_minor=labour_minor, tax_minor=tax_minor,
        covered_minor=covered_minor, customer_payable_minor=payable,
        price_book_version=book.version, tax_policy_version=tax.version,
        status="proposed", valid_until=utcnow() + timedelta(days=7),
        idempotency_key=idempotency_key, request_hash=digest,
        created_by_user_id=user.id,
    )
    db.add(estimate)
    db.flush()
    add_audit(db, actor_user_id=user.id, action="billing.estimate_proposed",
              entity_type="service_estimate", entity_id=estimate.id,
              metadata={"ticket_id": str(ticket.id), "version": estimate.version,
                        "payable_minor": payable})
    db.flush()
    return estimate, True


def _estimate_payload(estimate: ServiceEstimate) -> dict:
    return {"estimate_id": str(estimate.id), "version": estimate.version,
            "lines": estimate.lines, "parts_minor": estimate.parts_minor,
            "labour_minor": estimate.labour_minor, "tax_minor": estimate.tax_minor,
            "covered_minor": estimate.covered_minor,
            "payable_minor": estimate.customer_payable_minor}


def decide_estimate(db: Session, user: User, estimate_id: uuid.UUID, decision: str,
                    estimate_version: int, note: str | None) -> ServiceEstimate:
    _require_roles(user, {CUSTOMER})
    estimate = db.scalar(
        select(ServiceEstimate).where(ServiceEstimate.id == estimate_id).with_for_update()
    )
    if estimate is None:
        raise AppError(404, "not_found", "Estimate not found.")
    ticket = db.get(ServiceTicket, estimate.ticket_id)
    assert ticket is not None
    if ticket.customer_user_id != user.id:
        raise AppError(404, "not_found", "Estimate not found.")
    if decision not in ("accepted", "rejected"):
        raise AppError(422, "validation_error", "Decision must be accepted or rejected.")
    if estimate_version != estimate.version:
        raise AppError(409, "stale_estimate",
                       "This estimate version is no longer current.")
    if estimate.status != "proposed":
        raise AppError(409, "invalid_transition", "This estimate was already answered.")
    if utcnow() > estimate.valid_until:
        estimate.status = "expired"
        db.flush()
        raise AppError(409, "estimate_expired", "This estimate expired; ask for a new version.")
    if decision == "rejected" and not (note and len(note.strip()) >= 3):
        raise AppError(422, "validation_error", "Rejecting an estimate needs a reason.")
    payload_hash = _digest(_estimate_payload(estimate))
    db.add(EstimateDecision(
        estimate_id=estimate.id, ticket_id=ticket.id, estimate_version=estimate.version,
        payload_hash=payload_hash, decision=decision, note=(note or None),
        customer_user_id=user.id,
    ))
    estimate.status = "accepted" if decision == "accepted" else "rejected"
    db.flush()
    db.add(
        ServiceTicketEvent(
            ticket_id=ticket.id, from_status=ticket.status, to_status=None,
            actor_user_id=user.id, action=f"estimate_{decision}", reason=note,
            evidence={"estimate_id": str(estimate.id), "version": estimate.version,
                      "payload_hash": payload_hash},
        )
    )
    ticket.updated_at = utcnow()
    add_audit(db, actor_user_id=user.id, action=f"billing.estimate_{decision}",
              entity_type="service_estimate", entity_id=estimate.id,
              metadata={"version": estimate.version})
    db.flush()
    return estimate


def create_invoice(db: Session, user: User, estimate_id: uuid.UUID,
                   idempotency_key: str) -> tuple[ServiceInvoice, bool]:
    _require_roles(user, SUPPORT)
    estimate = db.scalar(
        select(ServiceEstimate).where(ServiceEstimate.id == estimate_id).with_for_update()
    )
    if estimate is None:
        raise AppError(404, "not_found", "Estimate not found.")
    if estimate.status != "accepted":
        raise AppError(409, "estimate_not_accepted",
                       "Only a customer-accepted estimate version can be billed.")
    digest = _digest({"estimate_id": str(estimate.id), "version": estimate.version,
                      "payable": estimate.customer_payable_minor})
    keyed = db.scalar(
        select(ServiceInvoice).where(ServiceInvoice.idempotency_key == idempotency_key)
    )
    if keyed is not None:
        if (keyed.estimate_id != estimate.id or keyed.request_hash != digest):
            raise AppError(409, "idempotency_conflict",
                           "This Idempotency-Key was already used for a different invoice.")
        return keyed, False
    invoice = ServiceInvoice(
        reference=next_reference(db, "invoice", "INV"),
        estimate_id=estimate.id, estimate_version=estimate.version,
        ticket_id=estimate.ticket_id, lines=estimate.lines,
        parts_minor=estimate.parts_minor, labour_minor=estimate.labour_minor,
        tax_minor=estimate.tax_minor, covered_minor=estimate.covered_minor,
        customer_payable_minor=estimate.customer_payable_minor,
        status="outstanding", idempotency_key=idempotency_key, request_hash=digest,
        created_by_user_id=user.id,
    )
    db.add(invoice)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "invoice_exists",
                       "An invoice already exists for this estimate version.") from exc
    add_audit(db, actor_user_id=user.id, action="billing.invoice_created",
              entity_type="service_invoice", entity_id=invoice.id,
              metadata={"estimate_id": str(estimate.id),
                        "payable_minor": invoice.customer_payable_minor})
    db.flush()
    return invoice, True


def consume_invoice_parts(db: Session, user: User,
                          invoice_id: uuid.UUID) -> ServiceInvoice:
    _require_roles(user, WAREHOUSE)
    invoice = db.scalar(
        select(ServiceInvoice).where(ServiceInvoice.id == invoice_id).with_for_update()
    )
    if invoice is None:
        raise AppError(404, "not_found", "Invoice not found.")
    already_consumed = invoice.consumption_operation_id is not None
    operation = inventory_service.consume_service_invoice_stock(db, user, invoice.id)
    if already_consumed:
        return invoice
    invoice.consumption_operation_id = operation.id
    db.flush()
    add_audit(db, actor_user_id=user.id, action="billing.parts_consumed",
              entity_type="service_invoice", entity_id=invoice.id,
              metadata={"operation_id": str(operation.id)})
    db.flush()
    return invoice


def create_credit_note(db: Session, user: User, invoice_id: uuid.UUID, amount_minor: int,
                       reason: str) -> ServiceCreditNote:
    _require_roles(user, SUPPORT)
    if not isinstance(amount_minor, int) or amount_minor <= 0:
        raise AppError(422, "validation_error", "Credit amount must be positive paise.")
    if len(reason.strip()) < 10:
        raise AppError(422, "validation_error", "A credit note needs a recorded reason.")
    invoice = db.scalar(
        select(ServiceInvoice).where(ServiceInvoice.id == invoice_id).with_for_update()
    )
    if invoice is None:
        raise AppError(404, "not_found", "Invoice not found.")
    remaining = invoice.customer_payable_minor - invoice.credited_minor
    if amount_minor > remaining:
        raise AppError(422, "validation_error",
                       "A credit cannot exceed the outstanding invoice amount.")
    note = ServiceCreditNote(
        reference=next_reference(db, "credit_note", "CRN"),
        invoice_id=invoice.id, amount_minor=amount_minor, reason=reason.strip(),
        created_by_user_id=user.id,
    )
    db.add(note)
    db.flush()
    invoice.credited_minor += amount_minor
    if invoice.credited_minor == invoice.customer_payable_minor:
        invoice.status = "credited"
    db.flush()
    add_audit(db, actor_user_id=user.id, action="billing.credit_created",
              entity_type="service_credit_note", entity_id=note.id,
              metadata={"invoice_id": str(invoice.id), "amount_minor": amount_minor})
    db.flush()
    return note


def ticket_estimates(db: Session, user: User,
                     ticket_id: uuid.UUID) -> list[ServiceEstimate]:
    ticket = db.get(ServiceTicket, ticket_id)
    if ticket is None:
        raise AppError(404, "not_found", "Ticket not found.")
    if user.role_code in SUPPORT:
        pass
    elif user.role_code == CUSTOMER and ticket.customer_user_id == user.id:
        pass
    else:
        raise AppError(404, "not_found", "Ticket not found.")
    return list(
        db.scalars(
            select(ServiceEstimate)
            .where(ServiceEstimate.ticket_id == ticket.id)
            .order_by(ServiceEstimate.version)
        ).all()
    )


def list_invoices(db: Session, user: User,
                  ticket_id: uuid.UUID | None) -> list[ServiceInvoice]:
    statement = select(ServiceInvoice).order_by(ServiceInvoice.created_at.desc())
    if user.role_code in SUPPORT:
        pass
    elif user.role_code == CUSTOMER:
        statement = statement.where(
            ServiceInvoice.ticket_id.in_(
                select(ServiceTicket.id).where(ServiceTicket.customer_user_id == user.id))
        )
    else:
        _require_roles(user, SUPPORT)
    if ticket_id is not None:
        ticket = db.get(ServiceTicket, ticket_id)
        if ticket is None:
            raise AppError(404, "not_found", "Ticket not found.")
        if user.role_code == CUSTOMER and ticket.customer_user_id != user.id:
            raise AppError(404, "not_found", "Ticket not found.")
        statement = statement.where(ServiceInvoice.ticket_id == ticket_id)
    return list(db.scalars(statement).all())


def get_invoice(db: Session, user: User, invoice_id: uuid.UUID) -> ServiceInvoice:
    invoice = db.get(ServiceInvoice, invoice_id)
    if invoice is None:
        raise AppError(404, "not_found", "Invoice not found.")
    if user.role_code in SUPPORT:
        return invoice
    if user.role_code == CUSTOMER:
        ticket = db.get(ServiceTicket, invoice.ticket_id)
        if ticket is not None and ticket.customer_user_id == user.id:
            return invoice
    raise AppError(404, "not_found", "Invoice not found.")


def invoice_credit_notes(db: Session, user: User,
                         invoice_id: uuid.UUID) -> list[ServiceCreditNote]:
    invoice = get_invoice(db, user, invoice_id)
    return list(
        db.scalars(
            select(ServiceCreditNote)
            .where(ServiceCreditNote.invoice_id == invoice.id)
            .order_by(ServiceCreditNote.created_at)
        ).all()
    )
