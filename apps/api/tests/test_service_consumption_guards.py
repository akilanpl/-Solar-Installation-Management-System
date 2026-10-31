"""Real PostgreSQL safety guards for source-linked repair consumption.

Public workflows construct valid invoices. Deliberately malformed persisted
snapshots are changed only inside a rolled-back transaction to simulate
legacy/corrupt imports that cannot be submitted through the current API.
"""

import copy
import uuid

import pytest
from app.core.errors import AppError
from app.models.identity import User
from app.models.phase3 import StockLedger, StockOperation
from app.models.warranty import EstimateDecision, ServiceEstimate, ServiceInvoice
from app.services.inventory_service import consume_service_invoice_stock
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase4a_support import (
    _all_staff,
    _confirmed_order,
    _login,
    _receipt_validate,
    _support,
    _warehouse,
)
from tests.test_phase4b_billing import _estimate, _ready_flow

pytestmark = pytest.mark.database


def _invoice(client, application, *, consumable=True):
    _all_staff(application)
    ticket, _, _ = _ready_flow(client, application, consumable=consumable)
    proposed = _estimate(client, ticket["id"])
    assert proposed.status_code == 201, proposed.text
    estimate = proposed.json()
    accepted = client.post(f"/api/v1/estimates/{estimate['id']}/decision", json={
        "decision": "accepted", "estimate_version": estimate["version"],
    }, headers=_login(client, "customer", "leela@example.com", "Solarops123"))
    assert accepted.status_code == 200, accepted.text
    invoice = client.post("/api/v1/service-invoices", json={"estimate_id": estimate["id"]},
        headers={**_support(client), "Idempotency-Key": uuid.uuid4().hex})
    assert invoice.status_code == 201, invoice.text
    return invoice.json(), ticket


def _counts(db):
    return (db.scalar(select(func.count()).select_from(StockOperation)),
            db.scalar(select(func.count()).select_from(StockLedger)))


def test_missing_invoice_and_nonwarehouse_command_never_write_stock(client, application):
    _all_staff(application)
    with Session(application.state.engine) as db:
        before = _counts(db)
        warehouse = db.scalar(select(User).where(User.email == "wh@example.com"))
        sales = db.scalar(select(User).where(User.email == "sales@example.com"))
        for actor, code in ((warehouse, "not_found"), (sales, "forbidden")):
            with pytest.raises(AppError) as rejected:
                consume_service_invoice_stock(db, actor, uuid.uuid4())
            assert rejected.value.code == code
            assert _counts(db) == before
        db.rollback()


@pytest.mark.parametrize("corruption", [
    "missing_acceptance", "changed_version", "unaccepted_source", "changed_lines", "credited_invoice",
])
def test_persisted_invoice_source_guard_rejects_without_stock_writes(client, application, corruption):
    bill, _ = _invoice(client, application)
    with Session(application.state.engine) as db:
        invoice = db.get(ServiceInvoice, uuid.UUID(bill["id"]))
        estimate = db.get(ServiceEstimate, invoice.estimate_id)
        user = db.scalar(select(User).where(User.email == "wh@example.com"))
        before = _counts(db)
        if corruption == "missing_acceptance":
            decision = db.scalar(select(EstimateDecision).where(EstimateDecision.estimate_id == estimate.id))
            db.delete(decision)
        elif corruption == "changed_version":
            invoice.estimate_version += 1
        elif corruption == "unaccepted_source":
            estimate.status = "superseded"
        elif corruption == "changed_lines":
            invoice.lines = [{"kind": "part", "code": "CONN-MC4", "quantity": 99}]
        else:
            invoice.status = "credited"
        db.flush()
        with pytest.raises(AppError) as rejected:
            consume_service_invoice_stock(db, user, invoice.id)
        assert rejected.value.code == "estimate_not_accepted"
        assert invoice.consumption_operation_id is None
        assert _counts(db) == before
        db.rollback()


@pytest.mark.parametrize("parts, expected", [
    ([{"kind": "labour", "quantity": 1}], "nothing_to_consume"),
    ([{"kind": "part", "code": "CONN-MC4", "quantity": 0}], "validation_error"),
    ([{"kind": "part", "code": "CONN-MC4", "quantity": True}], "validation_error"),
    ([{"kind": "part", "code": "CONN-MC4", "quantity": "1"}], "validation_error"),
    ([{"kind": "part", "code": 42, "quantity": 1}], "validation_error"),
    ([{"kind": "part", "code": "NONEXISTENT-PART", "quantity": 1}], "unknown_component"),
    ([{"kind": "part", "code": "PANEL-550", "quantity": 1}], "serialized_replacement_required"),
])
def test_invalid_legacy_parts_never_create_partial_consumption(client, application, parts, expected):
    bill, _ = _invoice(client, application)
    with Session(application.state.engine) as db:
        invoice = db.get(ServiceInvoice, uuid.UUID(bill["id"]))
        estimate = db.get(ServiceEstimate, invoice.estimate_id)
        # Simulate the same legacy malformed snapshot in both source artifacts;
        # no API accepts these malformed service part values today.
        invoice.lines = copy.deepcopy(parts)
        estimate.lines = copy.deepcopy(parts)
        db.flush()
        before = _counts(db)
        user = db.scalar(select(User).where(User.email == "wh@example.com"))
        with pytest.raises(AppError) as rejected:
            consume_service_invoice_stock(db, user, invoice.id)
        assert rejected.value.code == expected
        assert invoice.consumption_operation_id is None
        assert _counts(db) == before
        db.rollback()


def test_consumption_preserves_another_orders_allocation_then_retries_once(client, application):
    bill, _ = _invoice(client, application)
    other = _confirmed_order(client, application, "allocation-owner@example.com")
    warehouse = _warehouse(client)
    _receipt_validate(client, warehouse, "CONN-MC4", "1")
    allocated = client.post("/api/v1/stock/allocations", json={
        "order_id": other["id"], "lines": [{"component_code": "CONN-MC4",
            "location_code": "MAIN", "quantity": 1}],
    }, headers=warehouse)
    assert allocated.status_code == 200, allocated.text
    path = f"/api/v1/service-invoices/{bill['id']}/consume"
    with Session(application.state.engine) as db:
        before = _counts(db)
    denied = client.post(path, headers=warehouse)
    assert denied.status_code == 409, denied.text
    assert denied.json()["error"]["code"] == "insufficient_stock"
    with Session(application.state.engine) as db:
        assert _counts(db) == before
        assert db.get(ServiceInvoice, uuid.UUID(bill["id"])).consumption_operation_id is None
    still_allocated = client.get(f"/api/v1/stock/allocations?order_id={other['id']}", headers=warehouse)
    assert still_allocated.status_code == 200, still_allocated.text
    connector = next(row for row in still_allocated.json() if row["component_code"] == "CONN-MC4")
    assert connector["quantity"] == 1 and connector["picked_quantity"] == 0
    _receipt_validate(client, warehouse, "CONN-MC4", "1")
    consumed = client.post(path, headers=warehouse)
    assert consumed.status_code == 200, consumed.text
    retried = client.post(path, headers=warehouse)
    assert retried.status_code == 200, retried.text
    assert retried.json()["consumption_operation_id"] == consumed.json()["consumption_operation_id"]
    with Session(application.state.engine) as db:
        operation_id = uuid.UUID(consumed.json()["consumption_operation_id"])
        outgoing = list(db.scalars(select(StockLedger).where(StockLedger.operation_id == operation_id)))
        assert len(outgoing) == 1 and outgoing[0].quantity_delta == -1
        assert outgoing[0].component_code == "CONN-MC4" and outgoing[0].location_code == "MAIN"
        assert db.scalar(select(func.sum(StockLedger.quantity_delta)).where(
            StockLedger.component_code == "CONN-MC4", StockLedger.location_code == "MAIN")) == 1


def test_unlinked_prior_operation_cannot_be_adopted_as_consumption(client, application):
    bill, ticket = _invoice(client, application)
    warehouse = _warehouse(client)
    prior = client.post("/api/v1/stock/operations", json={
        "operation_type": "delivery", "source_order_id": ticket["order_id"],
        "lines": [{"component_code": "CONN-MC4", "quantity": "1",
                   "from_location": "MAIN", "to_location": None}],
        "note": f"Accepted service invoice {bill['reference']}",
    }, headers={**warehouse, "Idempotency-Key": f"invoice-consume-{bill['id']}"})
    assert prior.status_code == 201, prior.text
    result = client.post(f"/api/v1/service-invoices/{bill['id']}/consume", headers=warehouse)
    assert result.status_code == 409, result.text
    assert result.json()["error"]["code"] == "invalid_consumption"
    with Session(application.state.engine) as db:
        invoice = db.get(ServiceInvoice, uuid.UUID(bill["id"]))
        assert invoice.consumption_operation_id is None
        operation = db.get(StockOperation, uuid.UUID(prior.json()["id"]))
        assert operation.status == "draft"
        assert db.scalar(select(func.count()).select_from(StockLedger).where(
            StockLedger.operation_id == operation.id)) == 0
        # A corrupt linkage must also be rejected, rather than marking consumed
        # merely because an existing draft operation's UUID was attached.
        invoice.consumption_operation_id = operation.id
        db.flush()
        user = db.scalar(select(User).where(User.email == "wh@example.com"))
        with pytest.raises(AppError) as rejected:
            consume_service_invoice_stock(db, user, invoice.id)
        assert rejected.value.code == "invalid_consumption"
        db.rollback()
