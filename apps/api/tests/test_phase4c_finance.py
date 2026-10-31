"""Real PostgreSQL/API finance invariants; all fixtures are synthetic local data."""

import threading
import uuid
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256

import pytest
from app.core.errors import AppError
from app.models.finance import FinanceEntry, FinanceEvidence, FinanceRecord
from app.models.identity import User
from app.models.phase3 import InstallationJob, StockLedger, StockOperation
from app.models.workflow import PaymentIntent, SalesOrder
from app.schemas import finance as s
from app.services import finance_service as f
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.test_phase4a_support import (
    _all_staff,
    _confirmed_order,
    _installed_order,
    _login,
    _tech_id,
)
from tests.test_phase4b_warranty import _admin

pytestmark = pytest.mark.database
TODAY = date.today().isoformat()


def admin_login(client):
    return _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")


def post(client, path, body, headers, status=201):
    response = client.post("/api/v1/finance/" + path, json=body, headers=headers)
    assert response.status_code == status, response.text
    return response.json()


def upload(client, headers, content=b"%PDF-1.4\nSynthetic local acceptance evidence\n%%EOF"):
    response = client.post(
        "/api/v1/finance/evidence",
        headers=headers,
        files={"file": ("evidence.pdf", content, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def foundation(client, application, staff=True):
    if staff:
        _all_staff(application)
    headers = _admin(client, application)
    ev = upload(client, headers)
    period = post(client, "periods", {"starts_on": "2020-01-01", "ends_on": "2040-12-31"}, headers)
    policy = post(
        client,
        "policies",
        {
            "key": "policy-local-test",
            "label": "Synthetic approved acceptance policy",
            "approval_reference": "LOCAL TEST ONLY business approval fixture",
            "effective_from": "2020-01-01",
            "effective_to": "2040-12-31",
            "recognition": "completed_installation_and_approved_service",
            "tax": "preserve_approved_source_snapshot",
            "posting_rules": "invoice_deferred_tax_on_issue_costs_on_approval",
        },
        headers,
    )
    return headers, ev, period, policy


def dated(policy):
    return {"posting_date": TODAY, "policy_id": policy["id"]}


def invoice(client, headers, policy, order):
    return post(
        client,
        "invoices",
        {**dated(policy), "source_kind": "order", "source_id": order["id"]},
        headers,
    )


def completed_order(client, application):
    from tests.test_installation_hardening import customer, prepared
    from tests.test_phase3_warehouse_installation import _technician

    job, code, _, _ = prepared(client, application)
    from tests.test_phase4a_support import _order_material, _receipt_validate, _warehouse

    warehouse = _warehouse(client)
    for component, quantity in _order_material(application, job["order_id"]):
        _receipt_validate(client, warehouse, component, str(quantity))
    delivery = client.post(
        "/api/v1/deliveries",
        json={"order_id": job["order_id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert delivery.status_code == 201, delivery.text
    for action in ["transit", "deliver", "confirm"]:
        response = client.post(
            f"/api/v1/deliveries/{delivery.json()['id']}/{action}", headers=warehouse
        )
        assert response.status_code == 200, response.text
    path = f"/api/v1/jobs/{job['id']}"
    summary = client.get(path + "/work-summary").json()
    assert (
        client.post(
            path + "/signature",
            json={
                "signature_ref": "Synthetic customer acceptance",
                "customer_confirmed": True,
                "summary_hash": summary["summary_hash"],
            },
            headers=customer(client),
        ).status_code
        == 200
    )
    tech = _technician(client)
    assert client.post(path + "/customer-otp", json={"code": code}, headers=tech).status_code == 200
    result = client.post(path + "/completion", headers=tech)
    assert result.status_code == 200, result.text
    with Session(application.state.engine) as db:
        order = db.get(SalesOrder, uuid.UUID(job["order_id"]))
        return {
            "id": str(order.id),
            "total_minor": order.total_minor,
            "tax_minor": order.tax_minor,
        }, result.json()


def test_source_invoice_duplicate_policy_period_rollback(client, application):
    headers, ev, period, policy = foundation(client, application)
    order = _confirmed_order(client, application)
    headers = admin_login(client)
    body = {**dated(policy), "source_kind": "order", "source_id": order["id"]}
    missing = client.post(
        "/api/v1/finance/invoices", json={**body, "policy_id": str(uuid.uuid4())}, headers=headers
    )
    assert missing.status_code == 404
    created = post(client, "invoices", body, headers)
    assert post(client, "invoices", body, headers)["id"] == created["id"]
    assert created["payload"]["total_minor"] == order["total_minor"]
    dashboard = client.get("/api/v1/finance/dashboard").json()
    assert dashboard["recognized_revenue_minor"] == dashboard["cash_minor"] == 0
    assert dashboard["receivables_minor"] == order["total_minor"]
    assert dashboard["jobs"][0]["complete"] is False
    assert (
        post(
            client,
            f"invoices/{created['id']}/recognize",
            {**dated(policy), "evidence_id": ev},
            headers,
            409,
        )["error"]["code"]
        == "completion_required"
    )
    post(
        client,
        f"periods/{period['id']}/close",
        {"evidence": "Local fixture reconciled"},
        headers,
        200,
    )
    with Session(application.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(FinanceRecord)
                .where(FinanceRecord.kind == "recognition")
            )
            == 0
        )
    # No finance artifacts survive a failed posting.
    assert (
        post(
            client,
            "costs",
            {
                **dated(policy),
                "order_id": order["id"],
                "kind": "expense",
                "amount_minor": 100,
                "evidence_id": ev,
                "description": "Test expense",
                "key": "rollback-expense",
            },
            headers,
            409,
        )["error"]["code"]
        == "period_closed"
    )
    with Session(application.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(FinanceRecord)
                .where(FinanceRecord.kind == "expense")
            )
            == 0
        )


def test_database_immutability_balance_seal_and_periods(client, application):
    headers, _, period, policy = foundation(client, application)
    with Session(application.state.engine) as db:
        actor = db.scalar(select(User).where(User.role_code == "admin"))
        actor_id = actor.id
    for table, change in [
        ("finance_records", "payload='{}'::jsonb"),
        ("finance_evidence", "sha256='bad'"),
    ]:
        with pytest.raises(IntegrityError), application.state.engine.begin() as conn:
            conn.execute(text(f"UPDATE {table} SET {change}"))
    with Session(application.state.engine) as db:
        source = db.get(FinanceRecord, uuid.UUID(policy["id"]))
        actor = db.get(User, actor_id)
        entry = f.post(
            db,
            actor,
            source,
            "fixture-balanced",
            date.today(),
            [("cash", 1, 0), ("customer_advance", 0, 1)],
        )
        entry_id = entry.id
        db.commit()
    for statement in [
        "UPDATE finance_lines SET debit_minor=9",
        "DELETE FROM finance_entries",
        f"INSERT INTO finance_lines(id,entry_id,account,debit_minor,credit_minor) VALUES ('{uuid.uuid4()}','{entry_id}','cash',1,0)",
    ]:
        with pytest.raises(IntegrityError), application.state.engine.begin() as conn:
            conn.execute(text(statement))
    with pytest.raises(IntegrityError), application.state.engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO finance_entries(id,source_event,record_id,period_id,posting_date,actor_id,request_hash) VALUES (:id,'bad-balance',:record,:period,CURRENT_DATE,:actor,'x')"
            ),
            {
                "id": uuid.uuid4(),
                "record": uuid.UUID(policy["id"]),
                "period": uuid.UUID(period["id"]),
                "actor": actor_id,
            },
        )
    assert (
        post(client, "periods", {"starts_on": TODAY, "ends_on": TODAY}, headers, 409)["error"][
            "code"
        ]
        == "overlapping_period"
    )
    post(client, f"periods/{period['id']}/close", {"evidence": "Local closure"}, headers, 200)
    with pytest.raises(IntegrityError), application.state.engine.begin() as conn:
        conn.execute(text("UPDATE finance_periods SET status='open'"))


def test_concurrent_source_event_posts_once(client, application):
    _, _, _, policy = foundation(client, application)
    barrier = threading.Barrier(2)
    results = []

    def worker():
        with Session(application.state.engine) as db:
            actor = db.scalar(select(User).where(User.role_code == "admin"))
            source = db.get(FinanceRecord, uuid.UUID(policy["id"]))
            barrier.wait(timeout=10)
            row = f.post(
                db,
                actor,
                source,
                "concurrent-event",
                date.today(),
                [("cash", 41, 0), ("customer_advance", 0, 41)],
            )
            results.append(row.id)
            db.commit()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
    assert len(results) == 2 and results[0] == results[1]
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(FinanceEntry)) == 1
        actor = db.scalar(select(User).where(User.role_code == "admin"))
        source = db.get(FinanceRecord, uuid.UUID(policy["id"]))
        with pytest.raises(AppError, match="different content"):
            f.post(
                db,
                actor,
                source,
                "concurrent-event",
                date.today(),
                [("cash", 42, 0), ("customer_advance", 0, 42)],
            )


@pytest.mark.parametrize("amount", [1.5, True, "100", -1, 9_000_000_000_001])
def test_money_validation_strict(client, application, amount):
    headers, ev, _, policy = foundation(client, application)
    response = client.post(
        "/api/v1/finance/costs",
        json={
            **dated(policy),
            "order_id": str(uuid.uuid4()),
            "kind": "expense",
            "amount_minor": amount,
            "evidence_id": ev,
            "description": "Test expense",
            "key": "strict",
        },
        headers=headers,
    )
    assert response.status_code == 422, response.text


def test_roles_and_evidence_integrity(client, application):
    headers, ev, _, _ = foundation(client, application)
    data = client.get(f"/api/v1/finance/evidence/{ev}")
    assert data.headers["x-artifact-sha256"] == sha256(data.content).hexdigest()
    for identifier in ["EMP-TECH-901", "EMP-SALES-901", "EMP-WH-901", "EMP-SUP-901"]:
        _login(client, "employee", identifier, "Staffpass123")
        for path in ["dashboard", "journal", "periods", "reports/profit.csv"]:
            assert client.get("/api/v1/finance/" + path).status_code == 403
        assert client.get(f"/api/v1/finance/evidence/{ev}").status_code == 404
    client.cookies.clear()
    assert client.get("/api/v1/finance/dashboard").status_code == 401


@pytest.mark.parametrize("loss", [False, True])
def test_profit_reconciles_negative_profit_and_export(client, application, loss):
    # The inherited completion fixture creates its own employees.
    order, job = completed_order(client, application)
    headers, ev, _, policy = foundation(client, application, staff=False)
    bill = invoice(client, headers, policy, order)
    recognized = post(
        client, f"invoices/{bill['id']}/recognize", {**dated(policy), "evidence_id": ev}, headers
    )
    with Session(application.state.engine) as db:
        movements = list(
            db.scalars(
                select(StockLedger)
                .join(StockOperation, StockOperation.id == StockLedger.operation_id)
                .where(
                    StockOperation.source_order_id == uuid.UUID(order["id"]),
                    StockOperation.status == "done",
                    StockLedger.quantity_delta < 0,
                )
            )
        )
        ids = [str(row.id) for row in movements]
    assert ids
    with Session(application.state.engine) as db:
        source_order = db.get(SalesOrder, uuid.UUID(order["id"]))
        payment = db.scalar(
            select(PaymentIntent).where(PaymentIntent.quotation_id == source_order.quotation_id)
        )
        payment_id = str(payment.id)
    post(
        client,
        "receipts/import",
        {
            **dated(policy),
            "order_id": order["id"],
            "payment_id": payment_id,
            "invoice_id": bill["id"],
        },
        headers,
    )
    costs = 0
    for ledger_id in ids:
        amount = order["total_minor"] if loss else 100
        post(
            client,
            "costs",
            {
                **dated(policy),
                "order_id": order["id"],
                "kind": "material",
                "ledger_id": ledger_id,
                "amount_minor": amount,
                "evidence_id": ev,
                "description": "Evidenced actual inventory cost fixture",
                "key": ledger_id,
            },
            headers,
        )
        costs += amount
    post(
        client,
        "completeness",
        {
            "order_id": order["id"],
            "evidence_id": ev,
            "labour_complete": True,
            "expenses_complete": True,
            "note": "Synthetic complete source reconciliation",
            "key": "complete",
        },
        headers,
    )
    report = client.get("/api/v1/finance/dashboard").json()
    profit = report["jobs"][0]
    expected = order["total_minor"] - order["tax_minor"] - costs
    assert profit["profit_minor"] == expected
    assert (expected < 0) == loss
    assert profit["complete"] is True, profit
    assert recognized["id"] in profit["source_record_ids"]
    exported = client.get("/api/v1/finance/reports/profit.csv")
    assert str(expected) in exported.text
    assert exported.headers["x-artifact-sha256"] == sha256(exported.content).hexdigest()
    assert exported.content == client.get("/api/v1/finance/reports/profit.csv").content
    # Reverse recognized revenue without mutating the original invoice.
    journal = client.get("/api/v1/finance/journal").json()
    entry = next(e for e in journal if e["source_event"] == f"recognition:{bill['id']}")
    reversal = {"posting_date": TODAY, "reason": "Correct recognition timing", "evidence_id": ev}
    result = post(client, f"journal/{entry['id']}/reverse", reversal, headers)
    assert post(client, f"journal/{entry['id']}/reverse", reversal, headers)["id"] == result["id"]
    assert client.get("/api/v1/finance/dashboard").json()["recognized_revenue_minor"] == 0


def test_cash_advance_is_not_revenue_and_allocates_once(client, application):
    headers, _, _, policy = foundation(client, application)
    order = _confirmed_order(client, application)
    headers = admin_login(client)
    with Session(application.state.engine) as db:
        payment = db.scalar(
            select(PaymentIntent).where(
                PaymentIntent.quotation_id == uuid.UUID(order["quotation_id"])
            )
        )
        payment_id = str(payment.id)
    body = {**dated(policy), "order_id": order["id"], "payment_id": payment_id}
    receipt = post(client, "receipts/import", body, headers)
    assert post(client, "receipts/import", body, headers)["id"] == receipt["id"]
    dashboard = client.get("/api/v1/finance/dashboard").json()
    assert dashboard["recognized_revenue_minor"] == 0
    assert dashboard["cash_minor"] == dashboard["advances_minor"] == order["total_minor"]
    bill = invoice(client, headers, policy, order)
    allocation = {
        **dated(policy),
        "receipt_id": receipt["id"],
        "invoice_id": bill["id"],
        "amount_minor": order["total_minor"],
        "key": "allocate",
    }
    row = post(client, "advances/allocate", allocation, headers)
    assert post(client, "advances/allocate", allocation, headers)["id"] == row["id"]
    assert (
        post(client, "advances/allocate", {**allocation, "key": "over"}, headers, 409)["error"][
            "code"
        ]
        == "over_allocation"
    )
    dashboard = client.get("/api/v1/finance/dashboard").json()
    assert (
        dashboard["receivables_minor"]
        == dashboard["advances_minor"]
        == dashboard["recognized_revenue_minor"]
        == 0
    )


def test_invoice_credit_tax_snapshot_and_cap(client, application):
    headers, ev, _, policy = foundation(client, application)
    order = _confirmed_order(client, application)
    headers = admin_login(client)
    bill = invoice(client, headers, policy, order)
    credit = {
        **dated(policy),
        "amount_minor": 118,
        "tax_minor": 18,
        "reason": "Approved partial cancellation",
        "evidence_id": ev,
        "key": "credit",
    }
    result = post(client, f"invoices/{bill['id']}/credits", credit, headers)
    assert result["payload"]["net_minor"] == 100
    assert (
        client.get("/api/v1/finance/dashboard").json()["receivables_minor"]
        == order["total_minor"] - 118
    )
    assert (
        post(
            client,
            f"invoices/{bill['id']}/credits",
            {**credit, "amount_minor": order["total_minor"], "key": "too-much"},
            headers,
            409,
        )["error"]["code"]
        == "credit_exceeds_balance"
    )

    other_order = _confirmed_order(client, application, "second-finance@example.com")
    headers = admin_login(client)
    other_bill = invoice(client, headers, policy, other_order)
    assert (
        post(client, f"invoices/{other_bill['id']}/credits", credit, headers, 409)["error"]["code"]
        == "idempotency_conflict"
    )


def test_technician_payable_rounding_adjustment_and_settlement(client, application):
    headers, ev, _, policy = foundation(client, application)
    order, _ = _installed_order(client, application)
    headers = admin_login(client)
    now = datetime.now(UTC)
    # Source job has recorded elapsed work; synthetic local clock span.
    tech_id = _tech_id(application, "tech@example.com")
    job = client.post(
        "/api/v1/jobs",
        json={"order_id": order["id"], "technician_user_id": tech_id},
        headers=_login(client, "employee", "EMP-SALES-901", "Staffpass123"),
    ).json()
    with Session(application.state.engine) as db:
        source = db.get(InstallationJob, uuid.UUID(job["id"]))
        source.arrival_at = now - timedelta(hours=1)
        source.completed_at = now
        source.status = "completed"
        db.commit()
    headers = admin_login(client)
    rate = post(
        client,
        "labour-rates",
        {
            "technician_id": tech_id,
            "effective_from": (now - timedelta(days=1)).isoformat(),
            "effective_to": (now + timedelta(days=1)).isoformat(),
            "hourly_minor": 1001,
            "evidence_id": ev,
            "key": "rate",
        },
        headers,
    )
    tech_headers = _login(client, "employee", "EMP-TECH-901", "Staffpass123")
    sheet = post(
        client,
        "timesheets",
        {
            "job_kind": "installation",
            "job_id": job["id"],
            "check_in": (now - timedelta(minutes=1)).isoformat(),
            "check_out": now.isoformat(),
            "note": "Actual test work",
            "key": "sheet",
        },
        tech_headers,
    )
    assert sheet["payload"]["hourly_minor"] == rate["payload"]["hourly_minor"]
    assert (
        post(
            client,
            f"timesheets/{sheet['id']}/review",
            {
                **dated(policy),
                "decision": "approved",
                "approved_minutes": 1,
                "note": "Manager approval",
                "evidence_id": ev,
            },
            tech_headers,
            403,
        )["error"]["code"]
        == "forbidden"
    )
    headers = admin_login(client)
    payable = post(
        client,
        f"timesheets/{sheet['id']}/review",
        {
            **dated(policy),
            "decision": "approved",
            "approved_minutes": 1,
            "note": "Manager approval",
            "evidence_id": ev,
        },
        headers,
    )
    assert payable["payload"]["amount_minor"] == 17
    dashboard = client.get("/api/v1/finance/dashboard").json()
    assert dashboard["payables_minor"] == 17 and dashboard["cash_minor"] == 0
    assert payable["payload"]["settlement_state"] == "unsettled"
    adjustment = {
        **dated(policy),
        "delta_minor": -2,
        "reason": "Approved minute valuation correction",
        "evidence_id": ev,
        "key": "adjust",
    }
    post(client, f"payables/{payable['id']}/adjustments", adjustment, headers)
    assert client.get("/api/v1/finance/dashboard").json()["payables_minor"] == 15
    settlement = {
        **dated(policy),
        "amount_minor": 15,
        "evidence_id": ev,
        "bank_reference": "SYNTHETIC-TRANSFER-EVIDENCE",
    }
    result = post(client, f"payables/{payable['id']}/settlements", settlement, headers)
    assert (
        post(client, f"payables/{payable['id']}/settlements", settlement, headers)["id"]
        == result["id"]
    )
    assert client.get("/api/v1/finance/dashboard").json()["payables_minor"] == 0
    assert (
        post(
            client,
            f"payables/{payable['id']}/settlements",
            {**settlement, "bank_reference": "OVER"},
            headers,
            409,
        )["error"]["code"]
        == "over_settlement"
    )

    tech_headers = _login(client, "employee", "EMP-TECH-901", "Staffpass123")
    other_sheet = post(
        client,
        "timesheets",
        {
            "job_kind": "installation",
            "job_id": job["id"],
            "check_in": (now - timedelta(minutes=2)).isoformat(),
            "check_out": (now - timedelta(minutes=1)).isoformat(),
            "note": "Second nonoverlapping minute of actual work",
            "key": "other-sheet",
        },
        tech_headers,
    )
    headers = admin_login(client)
    other_payable = post(
        client,
        f"timesheets/{other_sheet['id']}/review",
        {
            **dated(policy),
            "decision": "approved",
            "approved_minutes": 1,
            "note": "Second manager approval",
            "evidence_id": ev,
        },
        headers,
    )
    assert (
        post(client, f"payables/{other_payable['id']}/adjustments", adjustment, headers, 409)[
            "error"
        ]["code"]
        == "idempotency_conflict"
    )


def test_subsidy_missing_docs_ownership_consent_and_decision_evidence(client, application):
    headers, ev, _, _ = foundation(client, application)
    order = _confirmed_order(client, application)
    headers = admin_login(client)
    scheme = post(
        client,
        "subsidy-schemes",
        {
            "key": "test-scheme",
            "name": "Synthetic official checklist fixture",
            "official_url": "https://example.gov.in/checklist",
            "version": "LOCAL TEST version 1",
            "effective_from": "2020-01-01",
            "effective_to": "2040-12-31",
            "required_documents": ["identity", "electricity_bill"],
            "evidence_id": ev,
        },
        headers,
    )
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    case = post(
        client,
        "subsidies",
        {
            "order_id": order["id"],
            "scheme_id": scheme["id"],
            "consent_text": "I consent to the synthetic document workflow",
            "key": "case",
        },
        customer,
    )
    assert client.get(f"/api/v1/finance/subsidies/{case['id']}").json()["missing"] == [
        "electricity_bill",
        "identity",
    ]
    sales = _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    sales_ev = upload(client, sales)
    event = {
        "action": "reviewed",
        "note": "Checklist reviewed",
        "evidence_id": sales_ev,
        "external_reference": "REVIEW-LOCAL",
        "key": "review",
    }
    assert (
        post(client, f"subsidies/{case['id']}/events", event, sales, 409)["error"]["code"]
        == "documents_missing"
    )
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    for doc_type in ["identity", "electricity_bill"]:
        doc = upload(client, customer)
        post(
            client,
            f"subsidies/{case['id']}/documents",
            {"document_type": doc_type, "evidence_id": doc, "key": doc_type},
            customer,
        )
    sales = _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    post(client, f"subsidies/{case['id']}/events", event, sales)
    assert (
        post(
            client,
            f"subsidies/{case['id']}/events",
            {**event, "action": "approved", "key": "premature"},
            sales,
            409,
        )["error"]["code"]
        == "invalid_transition"
    )
    post(
        client,
        f"subsidies/{case['id']}/events",
        {
            **event,
            "action": "submitted",
            "key": "submitted",
            "external_reference": "LOCAL-SUBMISSION",
        },
        sales,
    )
    assert (
        post(
            client,
            f"subsidies/{case['id']}/events",
            {"action": "approved", "note": "Missing official evidence", "key": "bad"},
            sales,
            409,
        )["error"]["code"]
        == "submission_evidence_required"
    )
    post(
        client,
        f"subsidies/{case['id']}/events",
        {
            **event,
            "action": "rejected",
            "key": "decision",
            "external_reference": "SYNTHETIC-OFFICIAL-DECISION",
        },
        sales,
    )
    detail = client.get(f"/api/v1/finance/subsidies/{case['id']}").json()
    assert detail["state"] == "rejected" and len(detail["history"]) == 5
    from tests.conftest import signup_and_verify

    signup_and_verify(client, application, "other@example.com")
    _login(client, "customer", "other@example.com", "Solarops123")
    assert client.get(f"/api/v1/finance/subsidies/{case['id']}").status_code == 404


def test_approved_phase4b_service_bill_adapter(client, application):
    from tests.test_phase4b_billing import _estimate, _ready_flow

    _all_staff(application)
    ticket, _, _ = _ready_flow(client, application, labour_covered=False)
    estimate = _estimate(client, ticket["id"]).json()
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    decision = client.post(
        f"/api/v1/estimates/{estimate['id']}/decision",
        json={"decision": "accepted", "estimate_version": estimate["version"]},
        headers=customer,
    )
    assert decision.status_code == 200, decision.text
    support = _login(client, "employee", "EMP-SUP-901", "Staffpass123")
    source = client.post(
        "/api/v1/service-invoices",
        json={"estimate_id": estimate["id"]},
        headers={**support, "Idempotency-Key": "4c-service-source"},
    )
    assert source.status_code == 201, source.text
    headers = admin_login(client)
    ev = upload(client, headers)
    post(client, "periods", {"starts_on": "2020-01-01", "ends_on": "2040-12-31"}, headers)
    policy = post(
        client,
        "policies",
        {
            "key": "service-policy",
            "label": "Synthetic policy approval",
            "approval_reference": "LOCAL TEST ONLY",
            "effective_from": "2020-01-01",
            "effective_to": "2040-12-31",
            "recognition": "completed_installation_and_approved_service",
            "tax": "preserve_approved_source_snapshot",
            "posting_rules": "invoice_deferred_tax_on_issue_costs_on_approval",
        },
        headers,
    )
    bill = post(
        client,
        "invoices",
        {**dated(policy), "source_kind": "service_invoice", "source_id": source.json()["id"]},
        headers,
    )
    assert bill["payload"]["total_minor"] == source.json()["customer_payable_minor"]
    assert bill["payload"]["tax_minor"] == source.json()["tax_minor"]
    post(client, f"invoices/{bill['id']}/recognize", {**dated(policy), "evidence_id": ev}, headers)
    assert (
        client.get("/api/v1/finance/dashboard").json()["recognized_revenue_minor"]
        == bill["payload"]["net_minor"]
    )


@pytest.mark.parametrize(
    "case,expected",
    [
        ("order_missing", "not_found"),
        ("record_missing", "not_found"),
        ("record_wrong_kind", "not_found"),
        ("evidence_missing", "evidence_required"),
        ("evidence_foreign", "not_found"),
        ("empty_upload", "invalid_file_size"),
        ("large_upload", "invalid_file_size"),
        ("bad_upload", "invalid_file_type"),
        ("policy_dates", "invalid_dates"),
        ("period_dates", "invalid_dates"),
        ("expired_policy", "policy_not_effective"),
        ("unbalanced", "unbalanced"),
        ("empty_journal", "unbalanced"),
        ("changed_record", "idempotency_conflict"),
        ("missing_service", "not_found"),
        ("missing_reversal", "invalid_reversal"),
        ("bad_technician", "invalid_technician"),
        ("bad_rate_dates", "invalid_dates"),
        ("missing_job", "not_found"),
        ("invalid_payable", "invalid_payable"),
        ("invalid_scheme", "invalid_scheme"),
    ],
)
def test_guard_matrix_rollback(client, application, case, expected):
    _, ev, _, policy = foundation(client, application)
    with Session(application.state.engine) as db:
        admin = db.scalar(select(User).where(User.role_code == "admin"))
        tech = db.scalar(select(User).where(User.role_code == "technician"))
        source = db.get(FinanceRecord, uuid.UUID(policy["id"]))
        foreign = db.get(FinanceEvidence, uuid.UUID(ev))
        before = db.scalar(select(func.count()).select_from(FinanceRecord))
        with pytest.raises(AppError) as caught:
            if case == "order_missing":
                f.order_for(db, uuid.uuid4())
            elif case == "record_missing":
                f.get_record(db, uuid.uuid4())
            elif case == "record_wrong_kind":
                f.get_record(db, source.id, "invoice")
            elif case == "evidence_missing":
                f.evidence(db, admin, uuid.uuid4())
            elif case == "evidence_foreign":
                f.evidence(db, tech, foreign.id)
            elif case == "empty_upload":
                f.upload(db, admin, b"")
            elif case == "large_upload":
                f.upload(db, admin, b"x" * 5_000_001)
            elif case == "bad_upload":
                f.upload(db, admin, b"not a pdf")
            elif case == "policy_dates":
                f.create_policy(
                    db,
                    admin,
                    s.PolicyCreate(
                        **{
                            **source.payload,
                            "key": "invalid",
                            "effective_from": "2040-01-01",
                            "effective_to": "2020-01-01",
                        }
                    ),
                )
            elif case == "period_dates":
                f.create_period(
                    db, admin, s.PeriodCreate(starts_on="2040-01-01", ends_on="2020-01-01")
                )
            elif case == "expired_policy":
                f.policy(db, source.id, date(2041, 1, 1))
            elif case == "unbalanced":
                f.post(db, admin, source, "bad", date.today(), [("cash", 2, 0), ("revenue", 0, 1)])
            elif case == "empty_journal":
                f.post(db, admin, source, "bad", date.today(), [])
            elif case == "changed_record":
                f.record(db, admin, "policy", source.source_key, {"changed": True})
            elif case == "missing_service":
                f.issue_invoice(
                    db,
                    admin,
                    s.FinanceInvoiceCreate(
                        **dated(policy), source_kind="service_invoice", source_id=uuid.uuid4()
                    ),
                )
            elif case == "missing_reversal":
                f.reverse(
                    db,
                    admin,
                    uuid.uuid4(),
                    s.ReverseCreate(posting_date=TODAY, reason="Correction", evidence_id=ev),
                )
            elif case == "bad_technician":
                f.create_rate(
                    db,
                    admin,
                    s.RateCreate(
                        technician_id=admin.id,
                        effective_from=datetime.now(UTC),
                        effective_to=datetime.now(UTC) + timedelta(days=1),
                        hourly_minor=1,
                        evidence_id=ev,
                        key="bad-rate",
                    ),
                )
            elif case == "bad_rate_dates":
                f.create_rate(
                    db,
                    admin,
                    s.RateCreate(
                        technician_id=tech.id,
                        effective_from=datetime.now(UTC),
                        effective_to=datetime.now(UTC) - timedelta(days=1),
                        hourly_minor=1,
                        evidence_id=ev,
                        key="bad-rate",
                    ),
                )
            elif case == "missing_job":
                f.submit_timesheet(
                    db,
                    tech,
                    s.TimesheetCreate(
                        job_kind="repair",
                        job_id=uuid.uuid4(),
                        check_in=datetime.now(UTC) - timedelta(hours=1),
                        check_out=datetime.now(UTC),
                        note="Missing job",
                        key="missing-job",
                    ),
                )
            elif case == "invalid_payable":
                f.settle(
                    db,
                    admin,
                    source.id,
                    s.SettlementCreate(
                        **dated(policy),
                        amount_minor=1,
                        evidence_id=ev,
                        bank_reference="bad-payable",
                    ),
                )
            elif case == "invalid_scheme":
                f.create_scheme(
                    db,
                    admin,
                    s.SchemeCreate(
                        key="bad-scheme",
                        name="Synthetic scheme",
                        official_url="https://example.gov.in",
                        version="Test version",
                        effective_from="2020-01-01",
                        effective_to="2040-01-01",
                        required_documents=["identity", "identity"],
                        evidence_id=ev,
                    ),
                )
        assert caught.value.code == expected
        assert db.scalar(select(func.count()).select_from(FinanceRecord)) == before
        db.rollback()


def test_direct_receipt_duplicate_sandbox_and_wrong_source_guards(client, application):
    headers, _, _, policy = foundation(client, application)
    order = _confirmed_order(client, application)
    headers = admin_login(client)
    bill = invoice(client, headers, policy, order)
    with Session(application.state.engine) as db:
        payment = db.scalar(
            select(PaymentIntent).where(
                PaymentIntent.quotation_id == uuid.UUID(order["quotation_id"])
            )
        )
        payment_id = str(payment.id)
    body = {
        **dated(policy),
        "order_id": order["id"],
        "payment_id": payment_id,
        "invoice_id": bill["id"],
    }
    result = post(client, "receipts/import", body, headers)
    assert post(client, "receipts/import", body, headers)["id"] == result["id"]
    assert client.get("/api/v1/finance/dashboard").json()["receivables_minor"] == 0
    assert (
        post(client, "receipts/import", {**body, "invoice_id": None}, headers, 409)["error"]["code"]
        == "idempotency_conflict"
    )
    assert (
        post(client, "receipts/import", {**body, "payment_id": str(uuid.uuid4())}, headers, 409)[
            "error"
        ]["code"]
        == "payment_mismatch"
    )
    with Session(application.state.engine) as db:
        payment = db.get(PaymentIntent, uuid.UUID(payment_id))
        payment.is_test_only = True
        db.commit()
    assert (
        post(client, "receipts/import", body, headers, 409)["error"]["code"] == "unverified_payment"
    )


def test_subsidy_consent_withdrawal_and_authorized_document_download(client, application):
    headers, ev, _, _ = foundation(client, application)
    order = _confirmed_order(client, application)
    headers = admin_login(client)
    scheme = post(
        client,
        "subsidy-schemes",
        {
            "key": "consent-scheme",
            "name": "Synthetic checklist",
            "official_url": "https://example.gov.in",
            "version": "Test version",
            "effective_from": "2020-01-01",
            "effective_to": "2040-12-31",
            "required_documents": ["identity"],
            "evidence_id": ev,
        },
        headers,
    )
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    case = post(
        client,
        "subsidies",
        {
            "order_id": order["id"],
            "scheme_id": scheme["id"],
            "consent_text": "Consent for local tests",
            "key": "consent-case",
        },
        customer,
    )
    doc = upload(client, customer)
    assert (
        post(
            client,
            f"subsidies/{case['id']}/documents",
            {"document_type": "unknown", "evidence_id": doc, "key": "bad-doc"},
            customer,
            422,
        )["error"]["code"]
        == "invalid_document"
    )
    post(
        client,
        f"subsidies/{case['id']}/documents",
        {"document_type": "identity", "evidence_id": doc, "key": "valid-doc"},
        customer,
    )
    _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    assert client.get(f"/api/v1/finance/evidence/{doc}").status_code == 200
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    withdrawn = {
        "action": "consent_withdrawn",
        "note": "Withdraw synthetic consent",
        "key": "withdraw",
    }
    result = post(client, f"subsidies/{case['id']}/events", withdrawn, customer)
    assert post(client, f"subsidies/{case['id']}/events", withdrawn, customer)["id"] == result["id"]
    assert (
        post(
            client,
            f"subsidies/{case['id']}/documents",
            {"document_type": "identity", "evidence_id": doc, "key": "frozen"},
            customer,
            409,
        )["error"]["code"]
        == "invalid_transition"
    )
    assert (
        post(
            client,
            f"subsidies/{case['id']}/events",
            {**withdrawn, "key": "withdraw-again"},
            customer,
            409,
        )["error"]["code"]
        == "invalid_transition"
    )
    _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    assert client.get(f"/api/v1/finance/evidence/{doc}").status_code == 404
    headers = admin_login(client)
    assert client.get("/api/v1/finance/dashboard").json()["subsidy_status"] == {
        "consent_withdrawn": 1
    }
    assert len(client.get("/api/v1/finance/records?kind=subsidy_case").json()) == 1
    assert client.get("/api/v1/finance/journal?order_id=" + order["id"]).json() == []


def test_export_escapes_formula_text_but_preserves_numeric_negative_profit(client, application):
    import csv
    import io

    foundation(client, application)
    order = _confirmed_order(client, application)
    admin_login(client)
    with Session(application.state.engine) as db:
        source = db.get(SalesOrder, uuid.UUID(order["id"]))
        source.reference = "\t=1+1"
        db.commit()
    response = client.get("/api/v1/finance/reports/profit.csv")
    assert response.status_code == 200
    row = list(csv.DictReader(io.StringIO(response.text)))[0]
    assert row["reference"] == "'\t=1+1"
    assert row["order_id"] == order["id"]
    assert response.headers["x-artifact-sha256"] == sha256(response.content).hexdigest()


def test_history_orders_by_serialized_event_time_not_transaction_start(client, application):
    foundation(client, application)
    with Session(application.state.engine) as earlier_transaction:
        actor = earlier_transaction.scalar(select(User).where(User.role_code == "admin"))
        # The first transaction starts before B but records its event after B commits.
        with Session(application.state.engine) as later_transaction:
            other_actor = later_transaction.get(User, actor.id)
            first = f.record(
                later_transaction, other_actor, "chronology_fixture", "first", {"sequence": 1}
            )
            first_id = first.id
            later_transaction.commit()
        second = f.record(
            earlier_transaction, actor, "chronology_fixture", "second", {"sequence": 2}
        )
        second_id = second.id
        earlier_transaction.commit()
    with Session(application.state.engine) as db:
        assert [row.id for row in f.records(db, "chronology_fixture")] == [first_id, second_id]
