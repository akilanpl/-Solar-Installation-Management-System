import uuid
from datetime import UTC, datetime

import pytest
from app.models.coverage import ProductWarrantyPolicy, SerialWarranty
from app.services.coverage_service import add_months
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import (
    _all_staff,
    _confirmed_order,
    _customer,
    _login,
    _order_material,
    _receipt_material,
    _receipt_validate,
    _register_received_units,
    _staff,
    _warehouse,
)

pytestmark = pytest.mark.database


def _admin(client):
    return _login(client, "employee", "EMP-ADMIN-901", "Staffpass123")


def _policy(client, months=12):
    return client.post(
        "/api/v1/warranty-policies",
        json={
            "component_code": "PANEL-550",
            "months": months,
            "activation_event": "delivery",
            "terms": "Isolated test product terms, not a manufacturer promise.",
        },
        headers=_admin(client),
    )


def test_serial_policy_snapshot_activation_return_and_customer_isolation(client, application):
    _all_staff(application)
    _staff(application, "admin", "policy-admin@example.com", "EMP-ADMIN-901")
    first = _policy(client)
    assert first.status_code == 200, first.text
    order = _confirmed_order(client, application)
    changed = _policy(client, 24)
    assert changed.status_code == 200, changed.text
    wh = _warehouse(client)
    materials = dict(_order_material(application, order["id"]))
    receipt = _receipt_validate(client, wh, "PANEL-550", str(materials.pop("PANEL-550")))
    _receipt_material(client, wh, list(materials.items()))
    serial = client.post(
        "/api/v1/serials/scan",
        json={
            "serial_number": "TEST-COVERAGE-PANEL-1",
            "component_code": "PANEL-550",
            "operation_id": receipt["id"],
        },
        headers=wh,
    ).json()
    _register_received_units(client, wh, receipt, "PANEL-550", skip=1)
    assert (
        client.post(
            "/api/v1/serials/" + serial["id"] + "/assign",
            json={"order_id": order["id"]},
            headers=wh,
        ).status_code
        == 200
    )
    delivery = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**wh, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert delivery.status_code == 201, delivery.text
    for action in ["transit", "deliver", "confirm"]:
        assert (
            client.post(
                "/api/v1/deliveries/" + delivery.json()["id"] + "/" + action, headers=wh
            ).status_code
            == 200
        )
    _login(client, "customer", "leela@example.com", "Solarops123")
    coverage = client.get("/api/v1/orders/" + order["id"] + "/unit-warranties").json()
    assert len(coverage) == 6
    coverage.sort(key=lambda row: row["serial_number"] != "TEST-COVERAGE-PANEL-1")
    assert coverage[0]["serial_number"] == "TEST-COVERAGE-PANEL-1"
    assert coverage[0]["policy"]["months"] == 12
    assert coverage[0]["policy"]["id"] == first.json()["id"]
    assert coverage[0]["delivery_id"] == delivery.json()["id"]
    _customer(client, application, "other-coverage@example.com")
    assert client.get("/api/v1/orders/" + order["id"] + "/unit-warranties").status_code == 404
    wh = _warehouse(client)
    line = next(item for item in delivery.json()["lines"] if item["component_code"] == "PANEL-550")
    returned = client.post(
        "/api/v1/stock/returns",
        json={
            "delivery_line_id": line["id"],
            "quantity": 1,
            "reason": "Test damaged serialized unit",
            "serial_id": serial["id"],
        },
        headers={**wh, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert returned.status_code == 200, returned.text
    inspected = client.post(
        "/api/v1/stock/returns/" + returned.json()["id"] + "/inspection",
        json={"disposition": "damaged", "note": "Test fixture damage inspection"},
        headers=_admin(client),
    )
    assert inspected.status_code == 200, inspected.text
    _login(client, "customer", "leela@example.com", "Solarops123")
    rows = client.get("/api/v1/orders/" + order["id"] + "/unit-warranties").json()
    rows.sort(key=lambda row: row["serial_number"] != "TEST-COVERAGE-PANEL-1")
    assert rows[0]["status"] == "void"
    assert sum(row["status"] == "active" for row in rows) == 5
    assert rows[0]["void_reason"]
    with Session(application.state.engine) as db:
        assert db.get(ProductWarrantyPolicy, uuid.UUID(first.json()["id"])).months == 12
        assert len(list(db.scalars(select(SerialWarranty)))) == 6


def test_recorded_receipts_are_owner_scoped_and_not_provider_claims(client, application):
    _all_staff(application)
    _confirmed_order(client, application)
    _login(client, "customer", "leela@example.com", "Solarops123")
    rows = client.get("/api/v1/payments/receipts")
    assert rows.status_code == 200, rows.text
    assert len(rows.json()) == 1
    assert rows.json()[0]["payment"]["method"] == "cash"
    assert "not provider settlement" in rows.json()[0]["notice"]
    _customer(client, application, "receipt-other@example.com")
    assert client.get("/api/v1/payments/receipts").json() == []
    _warehouse(client)
    assert client.get("/api/v1/payments/receipts").status_code == 403


def test_policy_month_end_uses_calendar_anniversary():
    assert add_months(datetime(2032, 1, 31, tzinfo=UTC), 1) == datetime(2032, 2, 29, tzinfo=UTC)
    assert add_months(datetime(2032, 2, 29, tzinfo=UTC), 12) == datetime(2033, 2, 28, tzinfo=UTC)
