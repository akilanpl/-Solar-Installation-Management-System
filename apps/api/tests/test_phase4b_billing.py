"""Phase 4B approved estimates and immutable billing.

Prices come from frozen order lines and admin-recorded books only. Money is
integer paise; labour prorates per minute rounded half up; tax applies to the
customer-payable subtotal rounded half up to the paise.
"""

import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.models.identity import User
from app.models.warranty import ServiceEstimate, ServiceInvoice
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase4a_support import (
    _all_staff,
    _create_ticket,
    _installed_order,
    _login,
    _order_material,
    _record_full_repair,
    _repair_job,
    _support,
    _tech_id,
    _technician,
    _triage,
    _warehouse,
)
from tests.test_phase4b_warranty import _admin, _decide, _policy

pytestmark = pytest.mark.database


def _pricing(client, admin, labour_rate=6000, parts=None, tax_bps=1800):
    book = client.post(
        "/api/v1/service-price-books",
        json={"label": "Company approved service rates",
              "labour_rates": {"repair_labour": labour_rate},
              "part_prices": parts or {},
              "effective_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()},
        headers=admin,
    )
    assert book.status_code == 201, book.text
    tax = client.post(
        "/api/v1/service-tax-policies",
        json={"label": "Approved service GST", "rate_bps": tax_bps,
              "effective_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()},
        headers=admin,
    )
    assert tax.status_code == 201, tax.text
    return book.json(), tax.json()


def _ready_flow(client, application, email="leela@example.com", *, consumable=False, **policy_kw):
    """Installed order, triaged ticket, submitted repair job, covered decision."""
    admin = _admin(client, application)
    _policy(client, admin, **policy_kw)
    _pricing(client, admin)
    order, serial = _installed_order(client, application, email)
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", email, "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    if consumable:
        technician = _technician(client)
        path = f"/api/v1/repair-jobs/{job['id']}"
        assert client.post(path + "/arrival", headers=technician).status_code == 200
        assert client.post(path + "/diagnostics", json={
            "findings": "Damaged connector needs replacement."}, headers=technician).status_code == 200
        now = datetime.now(UTC)
        work = client.post(path + "/work", json={
            "work_performed": "Replaced connector and tested continuity.",
            "work_started_at": (now - timedelta(minutes=15)).isoformat(),
            "work_finished_at": now.isoformat(),
            "parts_used": [{"component_code": "CONN-MC4", "quantity": 1}],
        }, headers=technician)
        assert work.status_code == 200, work.text
        assert client.post(path + "/submit", json={
            "summary": "Connector replaced; circuit verified."}, headers=technician).status_code == 200
    else:
        _record_full_repair(client, job["id"], _technician(client))
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.json()["verdict"] == "covered", decided.text
    order_detail = client.get(f"/api/v1/orders/{order['id']}", headers=_support(client)).json()
    return ticket, job, order_detail


def _estimate(client, ticket_id, key=None):
    return client.post(
        f"/api/v1/tickets/{ticket_id}/estimates",
        headers={**_support(client), "Idempotency-Key": key or uuid.uuid4().hex},
    )


def test_pricing_admin_only_and_validation(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    support = _support(client)
    assert client.post(
        "/api/v1/service-price-books",
        json={"label": "Support cannot record rates", "labour_rates": {},
              "part_prices": {},
              "effective_from": datetime.now(UTC).isoformat()},
        headers=support,
    ).status_code == 403
    admin = _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")
    bad = client.post(
        "/api/v1/service-price-books",
        json={"label": "Bad rates", "labour_rates": {"repair_labour": -5},
              "part_prices": {}, "effective_from": datetime.now(UTC).isoformat()},
        headers=admin,
    )
    assert bad.status_code == 422, bad.text
    assert client.post(
        "/api/v1/service-tax-policies",
        json={"label": "Bad tax", "rate_bps": -1,
              "effective_from": datetime.now(UTC).isoformat()},
        headers=admin,
    ).status_code == 422


def test_estimate_guards(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin)
    order, serial = _installed_order(client, application)
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    assert _estimate(client, ticket["id"]).json()["error"]["code"] == "work_required"
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    _record_full_repair(client, job["id"], _technician(client))
    assert _estimate(client, ticket["id"]).json()["error"]["code"] == "coverage_decision_required"
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.json()["verdict"] == "covered"
    assert _estimate(client, ticket["id"]).json()["error"]["code"] == "pricing_unavailable"


def test_covered_estimate_is_zero_payable(client, application):
    _all_staff(application)
    ticket, _, order_detail = _ready_flow(client, application)
    created = _estimate(client, ticket["id"])
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["version"] == 1 and body["status"] == "proposed"
    from app.models.workflow import SalesOrderLine
    with Session(application.state.engine) as db:
        panel_price = db.scalar(select(SalesOrderLine.unit_price_minor).where(
            SalesOrderLine.order_id == uuid.UUID(ticket["order_id"]),
            SalesOrderLine.component_code == "PANEL-550"))
    part = next(line for line in body["lines"] if line["kind"] == "part")
    assert part["code"] == "PANEL-550" and part["source"] == "order"
    assert part["unit_minor"] == panel_price
    assert part["covered_minor"] == part["line_total_minor"]
    labour = next(line for line in body["lines"] if line["kind"] == "labour")
    assert labour["quantity"] == 120
    assert labour["unit_minor"] == 6000
    assert labour["line_total_minor"] == 12000
    assert labour["covered_minor"] == 12000
    assert body["covered_minor"] == body["parts_minor"] + body["labour_minor"]
    assert body["customer_payable_minor"] == 0
    assert body["tax_minor"] == 0


def test_out_of_warranty_estimate_math(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin, duration=30)
    order, serial = _installed_order(client, application)
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    _record_full_repair(client, job["id"], _technician(client))
    admin = _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")
    _pricing(client, admin)
    far = (datetime.now(UTC) + timedelta(days=400)).isoformat()
    decided = _decide(client, _support(client), ticket["id"], serial, at=far)
    assert decided.json()["verdict"] == "not_covered", decided.text
    created = _estimate(client, ticket["id"])
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["covered_minor"] == 0
    subtotal = body["parts_minor"] + body["labour_minor"]
    assert body["tax_minor"] == (subtotal * 1800 + 5000) // 10000
    assert body["customer_payable_minor"] == subtotal + body["tax_minor"]


def test_mixed_coverage_and_book_fallback_price(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin, labour_covered=False)
    order, serial = _installed_order(client, application)
    materials = [code for code, _ in _order_material(application, order["id"])]
    fallback = next(code for code in ("CC-MPPT", "CONN-MC4", "EARTH", "BOX-AC")
                    if code not in materials)
    admin = _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")
    _pricing(client, admin, parts={fallback: 2500})
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    technician = _technician(client)
    assert client.post(f"/api/v1/repair-jobs/{job['id']}/arrival", headers=technician).status_code == 200
    assert client.post(
        f"/api/v1/repair-jobs/{job['id']}/diagnostics",
        json={"findings": "Charge controller failed along with the isolator issue."},
        headers=technician).status_code == 200
    now = datetime.now(UTC)
    work = client.post(
        f"/api/v1/repair-jobs/{job['id']}/work",
        json={"work_performed": "Replaced the charge controller and the isolator.",
              "work_started_at": (now - timedelta(hours=1)).isoformat(),
              "work_finished_at": now.isoformat(),
              "parts_used": [{"component_code": "PANEL-550", "quantity": 1},
                             {"component_code": fallback, "quantity": 2}]},
        headers=technician)
    assert work.status_code == 200, work.text
    assert client.post(
        f"/api/v1/repair-jobs/{job['id']}/submit",
        json={"summary": "Controller and isolator replaced; generation verified."},
        headers=technician).status_code == 200
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.json()["verdict"] == "covered"
    created = _estimate(client, ticket["id"])
    assert created.status_code == 201, created.text
    body = created.json()
    fallback_line = next(line for line in body["lines"] if line["code"] == fallback)
    assert fallback_line["source"] == "price_book"
    assert fallback_line["unit_minor"] == 2500
    assert fallback_line["line_total_minor"] == 5000
    assert body["covered_minor"] == body["parts_minor"]
    assert body["labour_minor"] > 0
    labour = next(line for line in body["lines"] if line["kind"] == "labour")
    assert labour["payable_minor"] == labour["line_total_minor"]
    assert body["tax_minor"] == (labour["line_total_minor"] * 1800 + 5000) // 10000
    assert body["customer_payable_minor"] == labour["line_total_minor"] + body["tax_minor"]


def test_unpriced_part_blocks_estimate(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin)
    _pricing(client, admin)
    order, serial = _installed_order(client, application)
    materials = {code for code, _ in _order_material(application, order["id"])}
    missing = next(code for code in ("CC-MPPT", "CONN-MC4", "EARTH", "BOX-AC")
                   if code not in materials)
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    technician = _technician(client)
    assert client.post(f"/api/v1/repair-jobs/{job['id']}/arrival", headers=technician).status_code == 200
    assert client.post(
        f"/api/v1/repair-jobs/{job['id']}/diagnostics",
        json={"findings": "Controller board failed and has no recorded price."},
        headers=technician).status_code == 200
    now = datetime.now(UTC)
    work = client.post(
        f"/api/v1/repair-jobs/{job['id']}/work",
        json={"work_performed": "Swapped the unpriced controller board.",
              "work_started_at": (now - timedelta(hours=1)).isoformat(),
              "work_finished_at": now.isoformat(),
              "parts_used": [{"component_code": missing, "quantity": 1}]},
        headers=technician)
    assert work.status_code == 200, work.text
    assert client.post(
        f"/api/v1/repair-jobs/{job['id']}/submit",
        json={"summary": "Controller swapped; generation verified stable."},
        headers=technician).status_code == 200
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.json()["verdict"] == "covered"
    blocked = _estimate(client, ticket["id"])
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "pricing_unavailable"
    assert missing in blocked.json()["error"]["message"]


def test_labour_rounding_and_tax_precision(client, application):
    _all_staff(application)
    admin = _admin(client, application)
    _policy(client, admin, labour_covered=False)
    _pricing(client, admin, labour_rate=1000, tax_bps=1800)
    order, serial = _installed_order(client, application)
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    technician = _technician(client)
    assert client.post(f"/api/v1/repair-jobs/{job['id']}/arrival", headers=technician).status_code == 200
    assert client.post(
        f"/api/v1/repair-jobs/{job['id']}/diagnostics",
        json={"findings": "One minute of actual adjustment work needed."},
        headers=technician).status_code == 200
    now = datetime.now(UTC)
    assert client.post(
        f"/api/v1/repair-jobs/{job['id']}/work",
        json={"work_performed": "Retorqued one terminal; verified output stable.",
              "work_started_at": (now - timedelta(minutes=1)).isoformat(),
              "work_finished_at": now.isoformat(), "parts_used": []},
        headers=technician).status_code == 200
    assert client.post(
        f"/api/v1/repair-jobs/{job['id']}/submit",
        json={"summary": "One minute of terminal work, output verified stable."},
        headers=technician).status_code == 200
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.json()["verdict"] == "covered"
    created = _estimate(client, ticket["id"])
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["labour_minor"] == 17
    assert body["tax_minor"] == 3
    assert body["customer_payable_minor"] == 20


def test_estimate_versions_and_decisions(client, application):
    _all_staff(application)
    ticket, _, _ = _ready_flow(client, application)
    first = _estimate(client, ticket["id"])
    assert first.json()["version"] == 1
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    no_reason = client.post(
        f"/api/v1/estimates/{first.json()['id']}/decision",
        json={"decision": "rejected", "estimate_version": 1},
        headers=customer)
    assert no_reason.status_code == 422, no_reason.text
    stale = client.post(
        f"/api/v1/estimates/{first.json()['id']}/decision",
        json={"decision": "accepted", "estimate_version": 2},
        headers=customer)
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "stale_estimate"
    rejected = client.post(
        f"/api/v1/estimates/{first.json()['id']}/decision",
        json={"decision": "rejected", "estimate_version": 1,
              "note": "The visit window does not work for me."},
        headers=customer)
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    second = _estimate(client, ticket["id"])
    assert second.json()["version"] == 2
    assert second.json()["status"] == "proposed"
    with Session(application.state.engine) as db:
        old = db.get(ServiceEstimate, uuid.UUID(first.json()["id"]))
        assert old is not None and old.status == "superseded"
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    accepted = client.post(
        f"/api/v1/estimates/{second.json()['id']}/decision",
        json={"decision": "accepted", "estimate_version": 2},
        headers=customer)
    assert accepted.status_code == 200, accepted.text
    duplicate = client.post(
        f"/api/v1/estimates/{second.json()['id']}/decision",
        json={"decision": "accepted", "estimate_version": 2},
        headers=customer)
    assert duplicate.status_code == 409, duplicate.text
    third = _estimate(client, ticket["id"])
    assert third.json()["version"] == 3
    with Session(application.state.engine) as db:
        kept = db.get(ServiceEstimate, uuid.UUID(second.json()["id"]))
        assert kept is not None and kept.status == "accepted"
        assert kept.customer_payable_minor == second.json()["customer_payable_minor"]
    with Session(application.state.engine) as db:
        doomed = db.get(ServiceEstimate, uuid.UUID(third.json()["id"]))
        assert doomed is not None
        doomed.valid_until = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    expired = client.post(
        f"/api/v1/estimates/{third.json()['id']}/decision",
        json={"decision": "accepted", "estimate_version": 3},
        headers=customer)
    assert expired.status_code == 409, expired.text
    assert expired.json()["error"]["code"] == "estimate_expired"


def test_invoice_lifecycle_and_credit_notes(client, application):
    _all_staff(application)
    ticket, _, _ = _ready_flow(client, application)
    estimate = _estimate(client, ticket["id"]).json()
    proposed = client.post(
        "/api/v1/service-invoices", json={"estimate_id": estimate["id"]},
        headers={**_support(client), "Idempotency-Key": uuid.uuid4().hex})
    assert proposed.status_code == 409, proposed.text
    assert proposed.json()["error"]["code"] == "estimate_not_accepted"
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    assert client.post(
        f"/api/v1/estimates/{estimate['id']}/decision",
        json={"decision": "accepted", "estimate_version": estimate["version"]},
        headers=customer).status_code == 200
    key = uuid.uuid4().hex
    first = client.post(
        "/api/v1/service-invoices", json={"estimate_id": estimate["id"]},
        headers={**_support(client), "Idempotency-Key": key})
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["status"] == "outstanding"
    assert body["customer_payable_minor"] == estimate["customer_payable_minor"]
    assert "paid" not in body["status"]
    replay = client.post(
        "/api/v1/service-invoices", json={"estimate_id": estimate["id"]},
        headers={**_support(client), "Idempotency-Key": key})
    assert replay.status_code == 200 and replay.json()["id"] == body["id"]
    support = _support(client)
    if body["customer_payable_minor"] > 0:
        half = body["customer_payable_minor"] // 2 or 1
        credit = client.post(
            f"/api/v1/service-invoices/{body['id']}/credit-notes",
            json={"amount_minor": half,
                  "reason": "Goodwill adjustment for the delayed visit window."},
            headers=support)
        assert credit.status_code == 201, credit.text
        reread = client.get(f"/api/v1/service-invoices/{body['id']}", headers=support).json()
        assert reread["credited_minor"] == half
        assert reread["status"] == "outstanding"
        assert reread["customer_payable_minor"] == body["customer_payable_minor"]
        rest = client.post(
            f"/api/v1/service-invoices/{body['id']}/credit-notes",
            json={"amount_minor": body["customer_payable_minor"] - half,
                  "reason": "Full waiver approved after the repeat fault visit."},
            headers=support)
        assert rest.status_code == 201, rest.text
        assert client.get(
            f"/api/v1/service-invoices/{body['id']}", headers=support).json()["status"] == "credited"
        over = client.post(
            f"/api/v1/service-invoices/{body['id']}/credit-notes",
            json={"amount_minor": 1, "reason": "Trying to credit beyond the invoice total."},
            headers=support)
        assert over.status_code == 422, over.text
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    mine = client.get("/api/v1/service-invoices", headers=customer)
    assert [row["id"] for row in mine.json()] == [body["id"]]
    assert client.post(
        "/api/v1/service-invoices", json={"estimate_id": estimate["id"]},
        headers={**customer, "Idempotency-Key": uuid.uuid4().hex}).status_code == 403


def test_consume_parts_validates_stock(client, application):
    from app.models.phase3 import StockLedger

    _all_staff(application)
    ticket, _, _ = _ready_flow(client, application, consumable=True)
    estimate = _estimate(client, ticket["id"]).json()
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    assert client.post(
        f"/api/v1/estimates/{estimate['id']}/decision",
        json={"decision": "accepted", "estimate_version": estimate["version"]},
        headers=customer).status_code == 200
    invoice = client.post(
        "/api/v1/service-invoices", json={"estimate_id": estimate["id"]},
        headers={**_support(client), "Idempotency-Key": uuid.uuid4().hex}).json()
    warehouse = _warehouse(client)
    short = client.post(f"/api/v1/service-invoices/{invoice['id']}/consume", headers=warehouse)
    assert short.status_code == 409, short.text
    assert short.json()["error"]["code"] == "insufficient_stock"
    with Session(application.state.engine) as db:
        row = db.get(ServiceInvoice, uuid.UUID(invoice["id"]))
        assert row is not None and row.consumption_operation_id is None
    received = client.post(
        "/api/v1/stock/operations",
        json={"operation_type": "receipt",
              "lines": [{"component_code": "CONN-MC4", "quantity": "3.0000",
                         "to_location": "MAIN"}]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex})
    assert received.status_code == 201, received.text
    operation_id = received.json()["id"]
    warehouse = _warehouse(client)
    assert client.post(
        f"/api/v1/stock/operations/{operation_id}/ready", headers=warehouse).status_code == 200
    assert client.post(
        f"/api/v1/stock/operations/{operation_id}/validate", headers=warehouse).status_code == 200
    consumed = client.post(
        f"/api/v1/service-invoices/{invoice['id']}/consume", headers=warehouse)
    assert consumed.status_code == 200, consumed.text
    assert consumed.json()["consumption_operation_id"] is not None
    with Session(application.state.engine) as db:
        from app.models.phase3 import StockOperation

        operation = db.get(StockOperation, uuid.UUID(consumed.json()["consumption_operation_id"]))
        assert operation.operation_type == "delivery" and operation.status == "done"
        assert operation.source_order_id == uuid.UUID(ticket["order_id"])
        assert operation.lines[0].component_code == "CONN-MC4"
        assert operation.lines[0].quantity == 1
        assert operation.lines[0].from_location == "MAIN"
    with Session(application.state.engine) as db:
        total = db.scalar(select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
            StockLedger.component_code == "CONN-MC4",
            StockLedger.location_code == "MAIN"))
        assert total == 2
    again = client.post(
        f"/api/v1/service-invoices/{invoice['id']}/consume", headers=_warehouse(client))
    assert again.status_code == 200
    assert again.json()["consumption_operation_id"] == consumed.json()["consumption_operation_id"]
    assert client.post(
        f"/api/v1/service-invoices/{invoice['id']}/consume",
        headers=_support(client)).status_code == 403


def test_concurrent_invoice_creation_single_winner(client, application):
    _all_staff(application)
    ticket, _, _ = _ready_flow(client, application)
    estimate = _estimate(client, ticket["id"]).json()
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    assert client.post(
        f"/api/v1/estimates/{estimate['id']}/decision",
        json={"decision": "accepted", "estimate_version": estimate["version"]},
        headers=customer).status_code == 200
    with Session(application.state.engine) as db:
        support_user = db.scalar(select(User).where(User.email == "support@example.com"))
        assert support_user is not None
        support_id = support_user.id
    from app.services import billing_service

    barrier = threading.Barrier(2)
    results: list[str] = []

    def _race(key: str) -> None:
        session = application.state.session_factory()
        try:
            user = session.get(User, support_id)
            assert user is not None
            barrier.wait()
            billing_service.create_invoice(
                session, user, uuid.UUID(estimate["id"]), key)
            session.commit()
            results.append("ok")
        except Exception as exc:  # noqa: BLE001 - racing threads report outcome only
            session.rollback()
            results.append(getattr(exc, "code", type(exc).__name__))
        finally:
            session.close()

    threads = [threading.Thread(target=_race, args=(f"race-{n}-{uuid.uuid4().hex}",))
               for n in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["invoice_exists", "ok"], results
    with Session(application.state.engine) as db:
        count = db.scalar(select(func.count()).select_from(ServiceInvoice).where(
            ServiceInvoice.estimate_id == uuid.UUID(estimate["id"])))
        assert count == 1



def test_consume_serialized_invoice_parts_requires_exact_replacement_link(client, application):
    from app.models.phase3 import StockOperation

    _all_staff(application)
    ticket, _, _ = _ready_flow(client, application)
    estimate = _estimate(client, ticket["id"]).json()
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    accepted = client.post(f"/api/v1/estimates/{estimate['id']}/decision",
        json={"decision": "accepted", "estimate_version": estimate["version"]}, headers=customer)
    assert accepted.status_code == 200, accepted.text
    invoice = client.post("/api/v1/service-invoices", json={"estimate_id": estimate["id"]},
        headers={**_support(client), "Idempotency-Key": uuid.uuid4().hex})
    assert invoice.status_code == 201, invoice.text
    invoice_id = invoice.json()["id"]
    with Session(application.state.engine) as db:
        before = db.scalar(select(func.count()).select_from(StockOperation))
    blocked = client.post(f"/api/v1/service-invoices/{invoice_id}/consume", headers=_warehouse(client))
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "serialized_replacement_required"
    with Session(application.state.engine) as db:
        assert db.get(ServiceInvoice, uuid.UUID(invoice_id)).consumption_operation_id is None
        assert db.scalar(select(func.count()).select_from(StockOperation)) == before
