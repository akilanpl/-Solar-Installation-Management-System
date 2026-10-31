"""Deleted/stale links must not invent records or mutate stock/security state."""

import uuid

import pytest
from app.models.phase3 import StockLedger, StockOperation
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import _all_staff, _sales, _technician, _warehouse

pytestmark = pytest.mark.database
MISSING = str(uuid.UUID(int=1))


def test_stale_sales_record_links_fail_without_fabricating_entities(client, application):
    _all_staff(application)
    _sales(client)
    for kind in ("surveys", "quotations", "orders", "payments"):
        result = client.get(f"/api/v1/{kind}/{MISSING}")
        assert result.status_code == 404, (kind, result.text)
        assert result.json()["error"]["code"] == "not_found"
    result = client.get(f"/api/v1/quotations/{MISSING}/payment-requirement")
    assert result.status_code == 404 and result.json()["error"]["code"] == "not_found"


def test_stale_warehouse_transitions_do_not_create_ledger_or_operation(client, application):
    _all_staff(application)
    headers = _warehouse(client)
    for path in (f"/stock/operations/{MISSING}", f"/deliveries/{MISSING}"):
        assert client.get("/api/v1" + path).status_code == 404
    for prefix, actions in (
        ("stock/operations", ("ready", "validate", "cancel")),
        ("deliveries", ("transit", "deliver", "confirm", "cancel")),
    ):
        for action in actions:
            result = client.post(f"/api/v1/{prefix}/{MISSING}/{action}", headers=headers)
            assert result.status_code == 404, (prefix, action, result.text)
            assert result.json()["error"]["code"] == "not_found"
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(StockLedger)) == 0
        assert db.scalar(select(func.count()).select_from(StockOperation)) == 0


def test_stale_technician_job_links_cannot_record_arrival_or_completion(client, application):
    _all_staff(application)
    headers = _technician(client)
    for tail in ("", "/work-summary"):
        response = client.get(f"/api/v1/jobs/{MISSING}{tail}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
    for action in ("arrival", "en-route", "completion"):
        result = client.post(f"/api/v1/jobs/{MISSING}/{action}", headers=headers)
        assert result.status_code == 404
        assert result.json()["error"]["code"] == "not_found"
