"""Regression: multi-line operations cannot collectively overdraw stock."""

import uuid

import pytest
from app.models.phase3 import StockLedger
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import (
    _all_staff,
    _manager,
    _receipt_validate,
    _warehouse,
)

pytestmark = pytest.mark.database


@pytest.mark.parametrize("operation_type", ["delivery", "transfer", "adjustment"])
def test_duplicate_lines_cannot_overdraw_location(client, application, operation_type):
    _all_staff(application)
    headers = _warehouse(client)
    _receipt_validate(client, headers, "PANEL-550", "10")
    line = {"component_code": "PANEL-550", "quantity": "6", "from_location": "MAIN"}
    if operation_type == "transfer":
        line["to_location"] = "SITE"
    if operation_type == "adjustment":
        headers = _manager(client)
        line["quantity"] = "-6"
    created = client.post(
        "/api/v1/stock/operations",
        json={
            "operation_type": operation_type,
            "lines": [line, line],
            "note": "Test counted-stock reconciliation",
        },
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    oid = created.json()["id"]
    assert client.post(f"/api/v1/stock/operations/{oid}/ready", headers=headers).status_code == 200
    result = client.post(f"/api/v1/stock/operations/{oid}/validate", headers=headers)
    assert result.status_code == 409, result.text
    with Session(application.state.engine) as db:
        total = db.scalar(
            select(func.sum(StockLedger.quantity_delta)).where(
                StockLedger.component_code == "PANEL-550", StockLedger.location_code == "MAIN"
            )
        )
        assert total == 10
    assert client.get(f"/api/v1/stock/operations/{oid}").json()["status"] == "ready"


@pytest.mark.parametrize("quantity", ["0.00001", "99999999999", "NaN", "Infinity"])
def test_stock_precision_and_finite_bounds_fail_before_database(client, application, quantity):
    _all_staff(application)
    result = client.post(
        "/api/v1/stock/operations",
        json={
            "operation_type": "receipt",
            "lines": [{"component_code": "PANEL-550", "quantity": quantity, "to_location": "MAIN"}],
        },
        headers={**_warehouse(client), "Idempotency-Key": uuid.uuid4().hex},
    )
    assert result.status_code == 422, result.text
