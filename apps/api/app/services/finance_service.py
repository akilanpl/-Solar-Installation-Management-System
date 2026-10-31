"""Finance commands compose within the inherited request transaction.

A transaction-scoped PostgreSQL advisory lock serializes this small subledger,
including period closes and reads. No commits here. Immutable source artifacts,
DB constraints and DB triggers defend the ledger independently of HTTP clients.
"""

import csv
import io
import json
import uuid
from datetime import UTC, date, datetime
from hashlib import sha256

from sqlalchemy import select, text

from app.core.errors import AppError
from app.models.finance import (
    FinanceEntry,
    FinanceEvidence,
    FinanceLine,
    FinancePeriod,
    FinanceRecord,
)
from app.models.identity import User
from app.models.phase3 import InstallationJob, StockLedger, StockOperation
from app.models.support import ServiceTicket, TicketRepairJob
from app.models.warranty import EstimateDecision, ServiceCreditNote, ServiceEstimate, ServiceInvoice
from app.models.workflow import PaymentIntent, Quotation, QuotationAcceptance, SalesOrder
from app.schemas import finance as s
from app.services.evidence_store import sniff_content_type
from app.services.payment_service import quotation_family_ids


def fail(code, message, status=409):
    raise AppError(status, code, message)


def require(user, *roles):
    if user.role_code not in roles:
        fail("forbidden", "Your role cannot perform this finance action.", 403)


def lock(db):
    db.execute(text("SELECT pg_advisory_xact_lock(404003)"))


def digest(payload):
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def get_record(db, record_id, kind=None):
    row = db.get(FinanceRecord, record_id)
    if row is None or (kind and row.kind != kind):
        fail("not_found", "Finance record not found.", 404)
    return row


def records(db, kind=None, order_id=None):
    query = select(FinanceRecord).order_by(FinanceRecord.created_at, FinanceRecord.id)
    if kind:
        query = query.where(FinanceRecord.kind == kind)
    if order_id:
        query = query.where(FinanceRecord.order_id == order_id)
    return list(db.scalars(query))


def record(db, user, kind, key, payload, order=None, policy_id=None):
    lock(db)
    payload = json.loads(json.dumps(payload, default=str))
    hashed = digest(
        {"payload": payload, "order_id": order.id if order else None, "policy_id": policy_id}
    )
    old = db.scalar(
        select(FinanceRecord).where(FinanceRecord.kind == kind, FinanceRecord.source_key == key)
    )
    if old:
        if old.request_hash != hashed:
            fail("idempotency_conflict", "This source key already has different content.")
        return old
    row = FinanceRecord(
        kind=kind,
        source_key=key,
        payload=payload,
        request_hash=hashed,
        order_id=order.id if order else None,
        customer_id=order.customer_user_id if order else None,
        actor_id=user.id,
        policy_id=policy_id,
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    return row


def order_for(db, order_id):
    order = db.get(SalesOrder, order_id)
    if not order:
        fail("not_found", "Order not found.", 404)
    return order


def evidence(db, user, evidence_id, owner=None):
    row = db.get(FinanceEvidence, evidence_id)
    if row is None or (owner is not None and row.owner_id != owner):
        fail("evidence_required", "An authorized uploaded evidence artifact is required.")
    if user.role_code != "admin" and row.owner_id != user.id:
        fail("not_found", "Evidence not found.", 404)
    return {"id": str(row.id), "sha256": row.sha256}


def upload(db, user, content):
    require(user, "admin", "customer", "sales", "technician")
    if not 0 < len(content) <= 5_000_000:
        fail("invalid_file_size", "Evidence must contain 1 to 5,000,000 bytes.", 422)
    mime = sniff_content_type(content)
    if mime is None:
        fail("invalid_file_type", "Upload a PDF or supported image.", 422)
    row = FinanceEvidence(
        owner_id=user.id, content=content, content_type=mime, sha256=sha256(content).hexdigest()
    )
    db.add(row)
    db.flush()
    return row


def policy(db, policy_id, posting_date):
    row = get_record(db, policy_id, "policy")
    if (
        not date.fromisoformat(row.payload["effective_from"])
        <= posting_date
        <= date.fromisoformat(row.payload["effective_to"])
    ):
        fail("policy_not_effective", "Approved finance policy is not effective on this date.")
    return row


def create_policy(db, user, payload):
    require(user, "admin")
    if payload.effective_to < payload.effective_from:
        fail("invalid_dates", "Policy end precedes start.", 422)
    return record(db, user, "policy", payload.key, payload.model_dump())


def create_period(db, user, payload):
    require(user, "admin")
    lock(db)
    if payload.ends_on < payload.starts_on:
        fail("invalid_dates", "Period end precedes start.", 422)
    if db.scalar(
        select(FinancePeriod.id).where(
            FinancePeriod.starts_on <= payload.ends_on, FinancePeriod.ends_on >= payload.starts_on
        )
    ):
        fail("overlapping_period", "Accounting periods cannot overlap.")
    row = FinancePeriod(**payload.model_dump(), actor_id=user.id, status="open")
    db.add(row)
    db.flush()
    return row


def post(db, user, source, event, posting_date, lines, reversal_of=None):
    lock(db)
    normalized = [(account, debit, credit) for account, debit, credit in lines if debit or credit]
    if not normalized or sum(d for _, d, _ in normalized) != sum(c for _, _, c in normalized):
        fail("unbalanced", "Journal debits and credits must balance and be nonzero.", 422)
    hashed = digest(
        {"record": source.id, "date": posting_date, "lines": normalized, "reversal": reversal_of}
    )
    old = db.scalar(select(FinanceEntry).where(FinanceEntry.source_event == event))
    if old:
        if old.request_hash != hashed:
            fail("idempotency_conflict", "Source event has already posted different content.")
        return old
    period = db.scalar(
        select(FinancePeriod)
        .where(FinancePeriod.starts_on <= posting_date, FinancePeriod.ends_on >= posting_date)
        .with_for_update()
    )
    if not period or period.status != "open":
        fail("period_closed", "Posting requires an open accounting period.")
    row = FinanceEntry(
        source_event=event,
        record_id=source.id,
        posting_date=posting_date,
        period_id=period.id,
        actor_id=user.id,
        request_hash=hashed,
        reversal_of=reversal_of,
    )
    db.add(row)
    db.flush()
    for account, debit, credit in normalized:
        db.add(
            FinanceLine(entry_id=row.id, account=account, debit_minor=debit, credit_minor=credit)
        )
    db.flush()
    return row


def entry_for(db, event):
    return db.scalar(select(FinanceEntry).where(FinanceEntry.source_event == event))


def active_entry(db, event):
    row = entry_for(db, event)
    if row and not db.scalar(select(FinanceEntry.id).where(FinanceEntry.reversal_of == row.id)):
        return row
    return None


def issue_invoice(db, user, payload: s.FinanceInvoiceCreate):
    require(user, "admin")
    lock(db)
    approved = policy(db, payload.policy_id, payload.posting_date)
    if payload.source_kind == "order":
        order = order_for(db, payload.source_id)
        quote = db.get(Quotation, order.quotation_id)
        if order.status != "confirmed" or not db.get(QuotationAcceptance, order.quotation_id):
            fail("unaccepted_source", "Invoice requires an originally accepted confirmed order.")
        net, tax = order.total_minor - order.tax_minor, order.tax_minor
        snapshot = {
            "reference": order.reference,
            "quotation_id": str(quote.id),
            "tax_rate_bps": quote.tax_rate_bps,
            "lines": [
                {
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_price_minor": line.unit_price_minor,
                    "line_total_minor": line.line_total_minor,
                }
                for line in order.lines
            ],
        }
    else:
        source = db.get(ServiceInvoice, payload.source_id)
        if not source:
            fail("not_found", "Approved service invoice not found.", 404)
        estimate = db.get(ServiceEstimate, source.estimate_id)
        accepted = db.scalar(
            select(EstimateDecision).where(
                EstimateDecision.estimate_id == estimate.id,
                EstimateDecision.decision == "accepted",
                EstimateDecision.estimate_version == source.estimate_version,
            )
        )
        if not accepted:
            fail("unaccepted_source", "The service estimate lacks customer acceptance.")
        ticket = db.get(ServiceTicket, source.ticket_id)
        order = order_for(db, ticket.order_id)
        net, tax = source.customer_payable_minor - source.tax_minor, source.tax_minor
        snapshot = {
            "reference": source.reference,
            "estimate_id": str(estimate.id),
            "estimate_version": source.estimate_version,
            "lines": source.lines,
            "tax_policy_version": estimate.tax_policy_version,
        }
    source_date = order.confirmed_at if payload.source_kind == "order" else source.created_at
    if payload.posting_date < source_date.astimezone(UTC).date() or order.currency_code != "INR":
        fail(
            "invalid_source_date_currency",
            "Invoice date and currency must agree with its INR source.",
        )
    if net < 0 or tax < 0 or net + tax <= 0:
        fail(
            "zero_or_invalid_bill",
            "A positive customer bill is required; covered zero bills are not receivables.",
        )
    row = record(
        db,
        user,
        "invoice",
        f"{payload.source_kind}:{payload.source_id}",
        {
            **payload.model_dump(),
            **snapshot,
            "net_minor": net,
            "tax_minor": tax,
            "total_minor": net + tax,
        },
        order,
        approved.id,
    )
    post(
        db,
        user,
        row,
        f"invoice:{row.id}",
        payload.posting_date,
        [("receivable", net + tax, 0), ("deferred_revenue", 0, net), ("tax_payable", 0, tax)],
    )
    return row


def recognize(db, user, invoice_id, payload):
    require(user, "admin")
    lock(db)
    invoice = get_record(db, invoice_id, "invoice")
    approved = policy(db, payload.policy_id, payload.posting_date)
    ev = evidence(db, user, payload.evidence_id)
    if payload.posting_date < date.fromisoformat(invoice.payload["posting_date"]):
        fail("invalid_dates", "Recognition cannot predate the invoice.")
    previous = entry_for(db, f"recognition:{invoice.id}")
    if previous and not active_entry(db, f"recognition:{invoice.id}"):
        fail(
            "recognition_reversed",
            "This recognition was reversed; a new approved adjustment workflow is required.",
        )
    if not active_entry(db, f"invoice:{invoice.id}"):
        fail("source_reversed", "Invoice posting is unavailable or reversed.")
    if invoice.payload["source_kind"] == "order":
        job = db.scalar(select(InstallationJob).where(InstallationJob.order_id == invoice.order_id))
        if not job or job.status != "completed" or not job.completed_at or not job.otp_verified:
            fail(
                "completion_required",
                "Installation completion and customer verification are required.",
            )
        if payload.posting_date < job.completed_at.date():
            fail("invalid_dates", "Revenue cannot predate source completion.")
    else:
        source = db.get(ServiceInvoice, uuid.UUID(invoice.payload["source_id"]))
        estimate = db.get(ServiceEstimate, source.estimate_id)
        job = db.get(TicketRepairJob, estimate.repair_job_id)
        if not job or job.status != "work_submitted":
            fail("completion_required", "Submitted service work is required.")
    credits = sum(
        r.payload["net_minor"]
        for r in records(db, "credit", invoice.order_id)
        if r.payload["invoice_id"] == str(invoice.id)
    )
    net = invoice.payload["net_minor"] - credits
    if net <= 0:
        fail("nothing_to_recognize", "No uncredited net revenue remains.")
    row = record(
        db,
        user,
        "recognition",
        str(invoice.id),
        {**payload.model_dump(), "invoice_id": str(invoice.id), "net_minor": net, "evidence": ev},
        order_for(db, invoice.order_id),
        approved.id,
    )
    post(
        db,
        user,
        row,
        f"recognition:{invoice.id}",
        payload.posting_date,
        [("deferred_revenue", net, 0), ("revenue", 0, net)],
    )
    return row


def import_payment(db, user, payload):
    require(user, "admin")
    lock(db)
    approved = policy(db, payload.policy_id, payload.posting_date)
    order = order_for(db, payload.order_id)
    payment = db.get(PaymentIntent, payload.payment_id)
    if not payment or payment.quotation_id not in quotation_family_ids(db, order.quotation_id):
        fail("payment_mismatch", "Payment does not belong to this order.")
    if (
        payment.status != "verified"
        or payment.is_test_only
        or payment.method != "cash"
        or not payment.transaction_reference
    ):
        fail(
            "unverified_payment",
            "Only evidenced, manually verified cash is supported. Sandbox events cannot settle finance.",
        )
    if payload.posting_date < payment.created_at.date():
        fail("invalid_dates", "Receipt cannot predate source payment.")
    target = "customer_advance"
    old = replay(db, user, "receipt", str(payment.id), payload, order, approved.id)
    if old:
        return old
    if payload.invoice_id:
        invoice = get_record(db, payload.invoice_id, "invoice")
        if invoice.order_id != order.id or invoice.payload["source_kind"] != "order":
            fail("invoice_mismatch", "Payment must reconcile to its order invoice.")
        if payment.amount_minor > invoice_balance(db, invoice):
            fail(
                "overpayment",
                "Payment exceeds the outstanding receivable; record it as an advance.",
            )
        target = "receivable"
    row = record(
        db,
        user,
        "receipt",
        str(payment.id),
        {
            **payload.model_dump(),
            "amount_minor": payment.amount_minor,
            "transaction_reference": payment.transaction_reference,
            "method": "manually_verified_cash",
        },
        order,
        approved.id,
    )
    post(
        db,
        user,
        row,
        f"receipt:{payment.id}",
        payload.posting_date,
        [("cash", payment.amount_minor, 0), (target, 0, payment.amount_minor)],
    )
    return row


def invoice_balance(db, invoice):
    credits = sum(
        r.payload["amount_minor"]
        for r in records(db, "credit", invoice.order_id)
        if r.payload["invoice_id"] == str(invoice.id)
    )
    received = sum(
        r.payload["amount_minor"]
        for r in records(db, "receipt", invoice.order_id)
        if r.payload.get("invoice_id") == str(invoice.id)
        and active_entry(db, f"receipt:{r.payload['payment_id']}")
    )
    allocated = sum(
        r.payload["amount_minor"]
        for r in records(db, "allocation", invoice.order_id)
        if r.payload["invoice_id"] == str(invoice.id)
    )
    return invoice.payload["total_minor"] - credits - received - allocated


def credit_invoice(db, user, invoice_id, payload):
    require(user, "admin")
    lock(db)
    invoice = get_record(db, invoice_id, "invoice")
    approved = policy(db, payload.policy_id, payload.posting_date)
    ev = evidence(db, user, payload.evidence_id)
    if payload.posting_date < date.fromisoformat(invoice.payload["posting_date"]):
        fail("invalid_dates", "Credit cannot predate the invoice.")
    if payload.tax_minor > payload.amount_minor:
        fail("invalid_tax", "Credit tax cannot exceed credit total.", 422)
    replay_key = (
        str(payload.source_credit_id)
        if invoice.payload["source_kind"] == "service_invoice"
        else payload.key
    )
    old = replay(
        db, user, "credit", replay_key, payload, order_for(db, invoice.order_id), approved.id
    )
    if old:
        return old
    if payload.amount_minor > invoice_balance(db, invoice):
        fail("credit_exceeds_balance", "Credit exceeds the uncollected invoice balance.")
    net = payload.amount_minor - payload.tax_minor
    prior = [
        r
        for r in records(db, "credit", invoice.order_id)
        if r.payload["invoice_id"] == str(invoice.id)
    ]
    if (
        sum(r.payload["net_minor"] for r in prior) + net > invoice.payload["net_minor"]
        or sum(r.payload["tax_minor"] for r in prior) + payload.tax_minor
        > invoice.payload["tax_minor"]
    ):
        fail("invalid_credit_split", "Credit exceeds the original net or tax snapshot.")
    if invoice.payload["source_kind"] == "service_invoice":
        source = (
            db.get(ServiceCreditNote, payload.source_credit_id)
            if payload.source_credit_id
            else None
        )
        if (
            not source
            or str(source.invoice_id) != invoice.payload["source_id"]
            or source.amount_minor != payload.amount_minor
        ):
            fail(
                "credit_source_required",
                "Service credits must match an actual Phase 4B credit note.",
            )
        key = str(source.id)
    else:
        key = payload.key
    row = record(
        db,
        user,
        "credit",
        key,
        {**payload.model_dump(), "invoice_id": str(invoice.id), "net_minor": net, "evidence": ev},
        order_for(db, invoice.order_id),
        approved.id,
    )
    target = "revenue" if active_entry(db, f"recognition:{invoice.id}") else "deferred_revenue"
    post(
        db,
        user,
        row,
        f"credit:{row.id}",
        payload.posting_date,
        [
            (target, net, 0),
            ("tax_payable", payload.tax_minor, 0),
            ("receivable", 0, payload.amount_minor),
        ],
    )
    return row


def reverse(db, user, entry_id, payload):
    require(user, "admin")
    lock(db)
    original = db.get(FinanceEntry, entry_id)
    if not original or original.reversal_of:
        fail("invalid_reversal", "Reverse an original posting only.")
    if payload.posting_date < original.posting_date:
        fail("invalid_dates", "Reversal cannot predate the original posting.")
    source = get_record(db, original.record_id)
    # Dependent business events need their own approved compensating workflow.
    if source.kind not in ("recognition",):
        fail(
            "dependent_reversal_blocked",
            "This source requires a credit/adjustment workflow; only recognition reversals are currently supported.",
        )
    invoice_id = source.payload["invoice_id"]
    if any(r.payload["invoice_id"] == invoice_id for r in records(db, "credit", source.order_id)):
        fail(
            "dependent_reversal_blocked",
            "Credited recognized revenue requires an approved accounting adjustment policy.",
        )
    ev = evidence(db, user, payload.evidence_id)
    row = record(
        db,
        user,
        "reversal",
        str(entry_id),
        {**payload.model_dump(), "entry_id": str(entry_id), "evidence": ev},
        order_for(db, source.order_id),
    )
    lines = list(db.scalars(select(FinanceLine).where(FinanceLine.entry_id == original.id)))
    post(
        db,
        user,
        row,
        f"reversal:{entry_id}",
        payload.posting_date,
        [(line.account, line.credit_minor, line.debit_minor) for line in lines],
        original.id,
    )
    return row


def create_rate(db, user, payload):
    require(user, "admin")
    lock(db)
    technician = db.get(User, payload.technician_id)
    if not technician or technician.role_code != "technician" or not technician.is_active:
        fail("invalid_technician", "An active technician is required.")
    if payload.effective_to <= payload.effective_from:
        fail("invalid_dates", "Rate end must follow start.", 422)
    ev = evidence(db, user, payload.evidence_id)
    for r in records(db, "labour_rate"):
        if (
            r.payload["technician_id"] == str(technician.id)
            and datetime.fromisoformat(r.payload["effective_from"]) < payload.effective_to
            and datetime.fromisoformat(r.payload["effective_to"]) > payload.effective_from
        ):
            if r.source_key == payload.key and r.payload == json.loads(
                json.dumps({**payload.model_dump(), "evidence": ev}, default=str)
            ):
                return r
            fail("overlapping_rate", "Effective labour rates cannot overlap.")
    return record(db, user, "labour_rate", payload.key, {**payload.model_dump(), "evidence": ev})


def submit_timesheet(db, user, payload):
    require(user, "technician")
    lock(db)
    model = InstallationJob if payload.job_kind == "installation" else TicketRepairJob
    job = db.get(model, payload.job_id)
    if not job or job.technician_user_id != user.id:
        fail("not_found", "Assigned job not found.", 404)
    end = job.completed_at if payload.job_kind == "installation" else job.work_finished_at
    if (
        not job.arrival_at
        or not end
        or payload.check_in < job.arrival_at
        or payload.check_out > end
    ):
        fail("job_time_mismatch", "Times must lie within recorded arrival and completed work.")
    seconds = int((payload.check_out - payload.check_in).total_seconds())
    if seconds <= 0 or seconds > 86400 or payload.check_out > datetime.now(UTC):
        fail("invalid_duration", "A timesheet must contain 1 second to 24 hours.", 422)
    for old in records(db, "timesheet"):
        p = old.payload
        if (
            p["technician_id"] == str(user.id)
            and p["key"] != payload.key
            and datetime.fromisoformat(p["check_in"]) < payload.check_out
            and datetime.fromisoformat(p["check_out"]) > payload.check_in
        ):
            fail("overlapping_timesheet", "Technician time overlaps an existing submission.")
    rates = [
        r
        for r in records(db, "labour_rate")
        if r.payload["technician_id"] == str(user.id)
        and datetime.fromisoformat(r.payload["effective_from"]) <= payload.check_in
        and datetime.fromisoformat(r.payload["effective_to"]) >= payload.check_out
    ]
    if len(rates) != 1:
        fail("rate_required", "One approved effective rate must cover the whole timesheet.")
    rate = rates[0]
    return record(
        db,
        user,
        "timesheet",
        f"{user.id}:{payload.key}",
        {
            **payload.model_dump(),
            "technician_id": str(user.id),
            "rate_id": str(rate.id),
            "hourly_minor": rate.payload["hourly_minor"],
            "maximum_minutes": seconds // 60,
        },
        order_for(db, job.order_id),
    )


def review_timesheet(db, user, sheet_id, payload):
    require(user, "admin")
    lock(db)
    sheet = get_record(db, sheet_id, "timesheet")
    approved = policy(db, payload.policy_id, payload.posting_date)
    ev = evidence(db, user, payload.evidence_id)
    if (
        payload.approved_minutes > sheet.payload["maximum_minutes"]
        or (payload.decision == "approved" and payload.approved_minutes == 0)
        or (payload.decision == "rejected" and payload.approved_minutes != 0)
    ):
        fail(
            "invalid_minutes",
            "Approved minutes must fit recorded time; rejected time has zero approved minutes.",
            422,
        )
    if payload.posting_date < datetime.fromisoformat(sheet.payload["check_out"]).date():
        fail("invalid_dates", "Payable cannot predate completed work.")
    # Half-up integer proration, no floating-point money.
    amount = (sheet.payload["hourly_minor"] * payload.approved_minutes + 30) // 60
    row = record(
        db,
        user,
        "timesheet_review",
        str(sheet.id),
        {
            **payload.model_dump(),
            "timesheet_id": str(sheet.id),
            "technician_id": sheet.payload["technician_id"],
            "hourly_minor": sheet.payload["hourly_minor"],
            "amount_minor": amount,
            "evidence": ev,
            "settlement_state": "unsettled",
        },
        order_for(db, sheet.order_id),
        approved.id,
    )
    if payload.decision == "approved":
        post(
            db,
            user,
            row,
            f"labour:{sheet.id}",
            payload.posting_date,
            [("labour_cost", amount, 0), ("technician_payable", 0, amount)],
        )
    return row


def create_cost(db, user, payload):
    require(user, "admin")
    lock(db)
    approved = policy(db, payload.policy_id, payload.posting_date)
    order = order_for(db, payload.order_id)
    ev = evidence(db, user, payload.evidence_id)
    key = payload.key
    if payload.kind == "material":
        ledger = db.get(StockLedger, payload.ledger_id) if payload.ledger_id else None
        operation = db.get(StockOperation, ledger.operation_id) if ledger else None
        if (
            not ledger
            or ledger.quantity_delta >= 0
            or not operation
            or operation.source_order_id != order.id
            or operation.status != "done"
        ):
            fail(
                "consumption_required", "Actual negative stock movement for this order is required."
            )
        if payload.posting_date < ledger.created_at.astimezone(UTC).date():
            fail("invalid_dates", "Cost cannot predate consumed stock.")
        key = str(ledger.id)
    elif payload.ledger_id:
        fail("invalid_ledger", "Expenses cannot reference a material movement.", 422)
    row = record(
        db, user, payload.kind, key, {**payload.model_dump(), "evidence": ev}, order, approved.id
    )
    post(
        db,
        user,
        row,
        f"cost:{row.id}",
        payload.posting_date,
        [
            ("material_cost" if payload.kind == "material" else "expense", payload.amount_minor, 0),
            (
                "inventory_clearing" if payload.kind == "material" else "expense_payable",
                0,
                payload.amount_minor,
            ),
        ],
    )
    return row


def settle(db, user, payable_id, payload):
    require(user, "admin")
    lock(db)
    payable = get_record(db, payable_id)
    if payable.kind != "timesheet_review" or payable.payload["decision"] != "approved":
        fail("invalid_payable", "An approved technician payable is required.")
    approved = policy(db, payload.policy_id, payload.posting_date)
    if payload.posting_date < date.fromisoformat(payable.payload["posting_date"]):
        fail("invalid_dates", "Settlement cannot predate its payable.")
    ev = evidence(db, user, payload.evidence_id)
    old = db.scalar(
        select(FinanceRecord).where(
            FinanceRecord.kind == "settlement", FinanceRecord.source_key == payload.bank_reference
        )
    )
    if old:
        if old.payload["payable_id"] != str(payable_id):
            fail("duplicate_settlement", "Bank reference is already allocated.")
        return record(
            db,
            user,
            "settlement",
            payload.bank_reference,
            {
                **payload.model_dump(),
                "payable_id": str(payable_id),
                "evidence": ev,
                "state": "manually_evidenced",
                "technician_id": payable.payload["technician_id"],
            },
            order_for(db, payable.order_id),
            approved.id,
        )
    paid = sum(
        r.payload["amount_minor"]
        for r in records(db, "settlement")
        if r.payload["payable_id"] == str(payable_id)
    )
    adjustments = sum(
        r.payload["delta_minor"]
        for r in records(db, "labour_adjustment")
        if r.payload["payable_id"] == str(payable_id)
    )
    if paid + payload.amount_minor > payable.payload["amount_minor"] + adjustments:
        fail("over_settlement", "Settlement exceeds outstanding approved payable.")
    row = record(
        db,
        user,
        "settlement",
        payload.bank_reference,
        {
            **payload.model_dump(),
            "payable_id": str(payable_id),
            "evidence": ev,
            "state": "manually_evidenced",
            "technician_id": payable.payload["technician_id"],
        },
        order_for(db, payable.order_id),
        approved.id,
    )
    post(
        db,
        user,
        row,
        f"settlement:{row.id}",
        payload.posting_date,
        [("technician_payable", payload.amount_minor, 0), ("cash", 0, payload.amount_minor)],
    )
    return row


def attest(db, user, payload):
    require(user, "admin")
    ev = evidence(db, user, payload.evidence_id)
    return record(
        db,
        user,
        "completeness",
        payload.key,
        {**payload.model_dump(), "evidence": ev},
        order_for(db, payload.order_id),
    )


def create_scheme(db, user, payload):
    require(user, "admin")
    if payload.effective_to < payload.effective_from or len(set(payload.required_documents)) != len(
        payload.required_documents
    ):
        fail("invalid_scheme", "Check scheme dates and unique checklist document types.", 422)
    ev = evidence(db, user, payload.evidence_id)
    return record(
        db,
        user,
        "subsidy_scheme",
        payload.key,
        {**payload.model_dump(), "official_source_evidence": ev},
    )


def subsidy_access(db, user, case_id):
    require(user, "customer", "sales", "admin")
    case = get_record(db, case_id, "subsidy_case")
    if user.role_code == "customer" and case.customer_id != user.id:
        fail("not_found", "Subsidy application not found.", 404)
    return case


def subsidy_state(db, case):
    events = [
        r
        for r in records(db, "subsidy_event", case.order_id)
        if r.payload["case_id"] == str(case.id)
    ]
    return events[-1].payload["action"] if events else "collecting"


def subsidy_missing(db, case):
    required = get_record(db, uuid.UUID(case.payload["scheme_id"]), "subsidy_scheme").payload[
        "required_documents"
    ]
    uploaded = {
        r.payload["document_type"]
        for r in records(db, "subsidy_document", case.order_id)
        if r.payload["case_id"] == str(case.id)
    }
    return sorted(set(required) - uploaded)


def create_subsidy(db, user, payload):
    require(user, "customer")
    lock(db)
    order = order_for(db, payload.order_id)
    if order.customer_user_id != user.id:
        fail("not_found", "Order not found.", 404)
    scheme = get_record(db, payload.scheme_id, "subsidy_scheme")
    today = datetime.now(UTC).date()
    if (
        not date.fromisoformat(scheme.payload["effective_from"])
        <= today
        <= date.fromisoformat(scheme.payload["effective_to"])
    ):
        fail("scheme_not_effective", "Checklist version is not currently effective.")
    existing = records(db, "subsidy_case", order.id)
    if existing and existing[0].source_key != f"{user.id}:{payload.key}":
        fail("application_exists", "This order already has a subsidy application.")
    return record(
        db,
        user,
        "subsidy_case",
        f"{user.id}:{payload.key}",
        {**payload.model_dump(), "scheme_snapshot": scheme.payload},
        order,
    )


def add_subsidy_document(db, user, case_id, payload):
    lock(db)
    case = subsidy_access(db, user, case_id)
    require(user, "customer")
    if subsidy_state(db, case) != "collecting":
        fail("invalid_transition", "Documents are frozen after review or consent withdrawal.")
    required = case.payload["scheme_snapshot"]["required_documents"]
    if payload.document_type not in required:
        fail("invalid_document", "Document type is not in this checklist.", 422)
    ev = evidence(db, user, payload.evidence_id, owner=user.id)
    return record(
        db,
        user,
        "subsidy_document",
        f"{case.id}:{payload.key}",
        {**payload.model_dump(), "case_id": str(case.id), "evidence": ev},
        order_for(db, case.order_id),
    )


def transition_subsidy(db, user, case_id, payload):
    lock(db)
    case = subsidy_access(db, user, case_id)
    old = db.scalar(
        select(FinanceRecord).where(
            FinanceRecord.kind == "subsidy_event",
            FinanceRecord.source_key == f"{case.id}:{payload.key}",
        )
    )
    ev = evidence(db, user, payload.evidence_id) if payload.evidence_id else None
    data = {**payload.model_dump(), "case_id": str(case.id), "evidence": ev}
    if old:
        return record(
            db,
            user,
            "subsidy_event",
            f"{case.id}:{payload.key}",
            data,
            order_for(db, case.order_id),
        )
    state = subsidy_state(db, case)
    if payload.action == "consent_withdrawn":
        require(user, "customer")
        if state in ("approved", "rejected", "consent_withdrawn"):
            fail("invalid_transition", "This case already has a terminal decision.")
    else:
        require(user, "sales", "admin")
        expected = {
            "reviewed": "collecting",
            "submitted": "reviewed",
            "approved": "submitted",
            "rejected": "submitted",
        }[payload.action]
        if state != expected:
            fail("invalid_transition", "Subsidy event does not follow the current state.")
        if subsidy_missing(db, case):
            fail(
                "documents_missing", "Complete the official checklist before review or submission."
            )
        if not ev or not payload.external_reference:
            fail(
                "submission_evidence_required",
                "Review, submission and official decisions require uploaded evidence and a reference.",
            )
    return record(
        db, user, "subsidy_event", f"{case.id}:{payload.key}", data, order_for(db, case.order_id)
    )


def visible_records(db, user, kind=None, order_id=None):
    require(user, "admin", "sales", "customer", "technician")
    lock(db)
    rows = records(db, kind, order_id)
    if user.role_code == "admin":
        return rows
    if user.role_code == "sales":
        return [r for r in rows if r.kind.startswith("subsidy_")]
    if user.role_code == "customer":
        return [
            r
            for r in rows
            if r.kind == "subsidy_scheme"
            or (
                r.customer_id == user.id
                and r.kind
                in ("invoice", "credit", "subsidy_case", "subsidy_document", "subsidy_event")
            )
        ]
    return [
        r
        for r in rows
        if (
            r.kind in ("timesheet", "timesheet_review", "labour_adjustment", "settlement")
            and r.payload["technician_id"] == str(user.id)
        )
        or (r.kind == "labour_rate" and r.payload["technician_id"] == str(user.id))
    ]


def journal_rows(db, user, order_id=None):
    require(user, "admin")
    lock(db)
    query = (
        select(FinanceEntry)
        .join(FinanceRecord, FinanceRecord.id == FinanceEntry.record_id)
        .order_by(FinanceEntry.created_at, FinanceEntry.id)
    )
    if order_id:
        query = query.where(FinanceRecord.order_id == order_id)
    return [
        s.JournalResponse(
            id=r.id,
            source_event=r.source_event,
            record_id=r.record_id,
            period_id=r.period_id,
            posting_date=r.posting_date,
            reversal_of=r.reversal_of,
            lines=[
                {
                    "account": line.account,
                    "debit_minor": line.debit_minor,
                    "credit_minor": line.credit_minor,
                }
                for line in db.scalars(
                    select(FinanceLine)
                    .where(FinanceLine.entry_id == r.id)
                    .order_by(FinanceLine.account)
                )
            ],
        )
        for r in db.scalars(query)
    ]


def dashboard(db, user):
    require(user, "admin")
    lock(db)
    all_records = records(db)
    journals = journal_rows(db, user)
    balances = {}
    per_order = {}
    by_id = {r.id: r for r in all_records}
    for entry in journals:
        source = by_id[entry.record_id]
        job_balances = per_order.setdefault(source.order_id, {})
        for line in entry.lines:
            account = line["account"]
            value = line["debit_minor"] - line["credit_minor"]
            balances[account] = balances.get(account, 0) + value
            job_balances[account] = job_balances.get(account, 0) + value
    jobs = []
    for order in db.scalars(select(SalesOrder).order_by(SalesOrder.reference)):
        sources = [r for r in all_records if r.order_id == order.id]
        b = per_order.get(order.id, {})
        movements = list(
            db.scalars(
                select(StockLedger)
                .join(StockOperation, StockOperation.id == StockLedger.operation_id)
                .where(
                    StockOperation.source_order_id == order.id,
                    StockOperation.status == "done",
                    StockLedger.quantity_delta < 0,
                )
            )
        )
        valued = {r.payload["ledger_id"] for r in sources if r.kind == "material"}
        missing = []
        if not movements or any(str(m.id) not in valued for m in movements):
            missing.append("actual_material_valuation")
        attestations = [r for r in sources if r.kind == "completeness"]
        if not attestations:
            missing.append("labour_and_expense_completeness_attestation")
        elif any(
            r.kind
            in (
                "material",
                "expense",
                "timesheet",
                "timesheet_review",
                "labour_adjustment",
                "invoice",
                "recognition",
                "credit",
            )
            and r.created_at > attestations[-1].created_at
            for r in sources
        ):
            missing.append("reconciliation_attestation_outdated")
        sheets = [r for r in sources if r.kind == "timesheet"]
        reviewed = {r.payload["timesheet_id"] for r in sources if r.kind == "timesheet_review"}
        if any(str(r.id) not in reviewed for r in sheets):
            missing.append("unreviewed_timesheets")
        invoices = [r for r in sources if r.kind == "invoice"]
        if not any(r.payload["source_kind"] == "order" for r in invoices) or any(
            not active_entry(db, f"recognition:{r.id}") for r in invoices
        ):
            missing.append("revenue_recognition")
        source_payments = list(
            db.scalars(
                select(PaymentIntent).where(
                    PaymentIntent.quotation_id.in_(quotation_family_ids(db, order.quotation_id)),
                    PaymentIntent.status == "verified",
                    PaymentIntent.is_test_only.is_(False),
                    PaymentIntent.method == "cash",
                )
            )
        )
        imported_payments = {r.payload["payment_id"] for r in sources if r.kind == "receipt"}
        if any(str(payment.id) not in imported_payments for payment in source_payments):
            missing.append("unreconciled_verified_cash_receipts")
        service_sources = list(
            db.scalars(
                select(ServiceInvoice)
                .join(ServiceTicket, ServiceTicket.id == ServiceInvoice.ticket_id)
                .where(ServiceTicket.order_id == order.id)
            )
        )
        imported_service_ids = {
            r.payload["source_id"]
            for r in invoices
            if r.payload["source_kind"] == "service_invoice"
        }
        if any(str(inv.id) not in imported_service_ids for inv in service_sources):
            missing.append("unimported_service_invoice")
        if any(
            any(line.get("kind") == "part" and line.get("quantity", 0) > 0 for line in inv.lines)
            and not inv.consumption_operation_id
            for inv in service_sources
        ):
            missing.append("unconsumed_service_materials")
        for inv in invoices:
            if inv.payload["source_kind"] == "service_invoice":
                source_credits = list(
                    db.scalars(
                        select(ServiceCreditNote).where(
                            ServiceCreditNote.invoice_id == uuid.UUID(inv.payload["source_id"])
                        )
                    )
                )
                imported = {
                    r.payload.get("source_credit_id") for r in sources if r.kind == "credit"
                }
                if any(str(c.id) not in imported for c in source_credits):
                    missing.append("unreconciled_phase4b_credit_notes")
        job = db.scalar(select(InstallationJob).where(InstallationJob.order_id == order.id))
        if not job or job.status != "completed":
            missing.append("installation_completion")
        revenue, material, labour, expense = (
            -b.get("revenue", 0),
            b.get("material_cost", 0),
            b.get("labour_cost", 0),
            b.get("expense", 0),
        )
        jobs.append(
            s.JobProfit(
                order_id=order.id,
                reference=order.reference,
                revenue_minor=revenue,
                material_minor=material,
                labour_minor=labour,
                expense_minor=expense,
                profit_minor=revenue - material - labour - expense,
                complete=not missing,
                missing=missing,
                source_record_ids=[r.id for r in sources],
            )
        )
    subsidies = {}
    for case in (r for r in all_records if r.kind == "subsidy_case"):
        state = subsidy_state(db, case)
        subsidies[state] = subsidies.get(state, 0) + 1
    outstanding = sum(
        1 for j in db.scalars(select(InstallationJob)) if j.status not in ("completed", "cancelled")
    )
    return s.DashboardResponse(
        recognized_revenue_minor=-balances.get("revenue", 0),
        cash_minor=balances.get("cash", 0),
        receivables_minor=balances.get("receivable", 0),
        payables_minor=-balances.get("technician_payable", 0) - balances.get("expense_payable", 0),
        advances_minor=-balances.get("customer_advance", 0),
        deferred_revenue_minor=-balances.get("deferred_revenue", 0),
        outstanding_jobs=outstanding,
        service_liability_minor=None,
        service_liability_state="unmeasured: approved warranty provision policy and cost estimates required",
        subsidy_status=subsidies,
        jobs=jobs,
    )


def csv_safe(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value


def export_report(db, user):
    report = dashboard(db, user)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        [
            "order_id",
            "reference",
            "recognized_revenue_paise",
            "material_paise",
            "labour_paise",
            "expenses_paise",
            "profit_paise",
            "complete",
            "missing",
            "source_record_ids",
        ]
    )
    for job in report.jobs:
        writer.writerow(
            [
                str(job.order_id),
                csv_safe(job.reference),
                job.revenue_minor,
                job.material_minor,
                job.labour_minor,
                job.expense_minor,
                job.profit_minor,
                job.complete,
                csv_safe("|".join(job.missing)),
                "|".join(map(str, job.source_record_ids)),
            ]
        )
    content = stream.getvalue().encode("utf-8")
    return content, sha256(content).hexdigest()


def replay(db, user, kind, key, payload, order, policy_id):
    """Validate original command content before mutable balance checks on retries."""
    old = db.scalar(
        select(FinanceRecord).where(FinanceRecord.kind == kind, FinanceRecord.source_key == key)
    )
    if old:
        if old.order_id != (order.id if order else None) or old.policy_id != policy_id:
            fail("idempotency_conflict", "This source key belongs to a different order or policy.")
        command = json.loads(json.dumps(payload.model_dump(), default=str))
        if any(old.payload.get(k) != value for k, value in command.items()):
            fail("idempotency_conflict", "This source key already has different content.")
        return old
    return None


def allocate_advance(db, user, payload):
    require(user, "admin")
    lock(db)
    receipt = get_record(db, payload.receipt_id, "receipt")
    invoice = get_record(db, payload.invoice_id, "invoice")
    if payload.posting_date < max(
        date.fromisoformat(receipt.payload["posting_date"]),
        date.fromisoformat(invoice.payload["posting_date"]),
    ):
        fail("invalid_dates", "Allocation cannot predate receipt or invoice.")
    if receipt.order_id != invoice.order_id or receipt.payload.get("invoice_id"):
        fail("invalid_advance", "Only an unallocated order advance can be applied to its invoice.")
    approved = policy(db, payload.policy_id, payload.posting_date)
    order = order_for(db, invoice.order_id)
    old = replay(db, user, "allocation", payload.key, payload, order, approved.id)
    if old:
        return old
    used = sum(
        r.payload["amount_minor"]
        for r in records(db, "allocation")
        if r.payload["receipt_id"] == str(receipt.id)
    )
    if used + payload.amount_minor > receipt.payload[
        "amount_minor"
    ] or payload.amount_minor > invoice_balance(db, invoice):
        fail("over_allocation", "Allocation exceeds available advance or invoice balance.")
    row = record(db, user, "allocation", payload.key, payload.model_dump(), order, approved.id)
    post(
        db,
        user,
        row,
        f"allocation:{row.id}",
        payload.posting_date,
        [("customer_advance", payload.amount_minor, 0), ("receivable", 0, payload.amount_minor)],
    )
    return row


def adjust_labour(db, user, payable_id, payload):
    require(user, "admin")
    lock(db)
    payable = get_record(db, payable_id, "timesheet_review")
    approved = policy(db, payload.policy_id, payload.posting_date)
    ev = evidence(db, user, payload.evidence_id)
    order = order_for(db, payable.order_id)
    old = replay(db, user, "labour_adjustment", payload.key, payload, order, approved.id)
    if old:
        if old.payload["payable_id"] != str(payable_id):
            fail("idempotency_conflict", "This adjustment key belongs to a different payable.")
        return old
    if payable.payload["decision"] != "approved" or payload.delta_minor == 0:
        fail("invalid_adjustment", "A nonzero adjustment to an approved payable is required.")
    prior = sum(
        r.payload["delta_minor"]
        for r in records(db, "labour_adjustment")
        if r.payload["payable_id"] == str(payable.id)
    )
    paid = sum(
        r.payload["amount_minor"]
        for r in records(db, "settlement")
        if r.payload["payable_id"] == str(payable.id)
    )
    if payable.payload["amount_minor"] + prior + payload.delta_minor < paid:
        fail(
            "adjustment_below_settled",
            "Adjustment cannot reduce the payable below actual settlements.",
        )
    row = record(
        db,
        user,
        "labour_adjustment",
        payload.key,
        {
            **payload.model_dump(),
            "payable_id": str(payable.id),
            "technician_id": payable.payload["technician_id"],
            "evidence": ev,
        },
        order,
        approved.id,
    )
    amount = abs(payload.delta_minor)
    lines = (
        [("labour_cost", amount, 0), ("technician_payable", 0, amount)]
        if payload.delta_minor > 0
        else [("technician_payable", amount, 0), ("labour_cost", 0, amount)]
    )
    post(db, user, row, f"adjustment:{row.id}", payload.posting_date, lines)
    return row
