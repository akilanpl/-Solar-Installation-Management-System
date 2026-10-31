"""Exact received-unit custody; all fixtures use the isolated test database."""

import uuid

import pytest
from app.models.phase3 import EquipmentSerial, StockLedger
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import (
    _all_staff,
    _confirmed_order,
    _manager,
    _receipt_validate,
    _register_received_units,
    _warehouse,
)

pytestmark = pytest.mark.database


def operation(client, headers, kind, lines, note="Test counted-stock reconciliation"):
    result = client.post(
        "/api/v1/stock/operations",
        json={"operation_type": kind, "lines": lines, "note": note},
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert result.status_code == 201, result.text
    identity = result.json()["id"]
    assert (
        client.post(f"/api/v1/stock/operations/{identity}/ready", headers=headers).status_code
        == 200
    )
    return client.post(f"/api/v1/stock/operations/{identity}/validate", headers=headers)


def received(client, application, quantity=2):
    _all_staff(application)
    headers = _warehouse(client)
    receipt = _receipt_validate(client, headers, "PANEL-550", str(quantity))
    return headers, _register_received_units(client, headers, receipt, "PANEL-550")


def test_transfer_updates_exact_unit_location_and_retains_history(client, application):
    headers, units = received(client, application)
    result = operation(
        client,
        headers,
        "transfer",
        [
            {
                "component_code": "PANEL-550",
                "quantity": "1",
                "from_location": "MAIN",
                "to_location": "SITE",
                "serial_ids": [units[0]["id"]],
            }
        ],
    )
    assert result.status_code == 200, result.text
    assert result.json()["lines"][0]["serial_numbers"] == [units[0]["serial_number"]]
    with Session(application.state.engine) as db:
        assert db.get(EquipmentSerial, uuid.UUID(units[0]["id"])).location_code == "SITE"
        assert db.get(EquipmentSerial, uuid.UUID(units[1]["id"])).location_code == "MAIN"
        assert db.scalar(select(func.sum(StockLedger.quantity_delta))) == 2
    missing = operation(
        client,
        headers,
        "transfer",
        [
            {
                "component_code": "PANEL-550",
                "quantity": "1",
                "from_location": "MAIN",
                "to_location": "SITE",
            }
        ],
    )
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "serials_required"
    wrong_source = operation(
        client,
        headers,
        "transfer",
        [
            {
                "component_code": "PANEL-550",
                "quantity": "1",
                "from_location": "MAIN",
                "to_location": "SITE",
                "serial_ids": [units[0]["id"]],
            }
        ],
    )
    assert wrong_source.status_code == 409
    assert wrong_source.json()["error"]["code"] == "invalid_serial_state"


def test_count_adjustment_requires_manager_reason_and_preserves_missing_identity(
    client, application
):
    headers, units = received(client, application, 1)
    line = {
        "component_code": "PANEL-550",
        "quantity": "-1",
        "to_location": "MAIN",
        "serial_ids": [units[0]["id"]],
    }
    denied = client.post(
        "/api/v1/stock/operations",
        json={"operation_type": "adjustment", "lines": [line], "note": "Test loss"},
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert denied.status_code == 403
    manager = _manager(client)
    missing = operation(client, manager, "adjustment", [line])
    assert missing.status_code == 200, missing.text
    with Session(application.state.engine) as db:
        unit = db.get(EquipmentSerial, uuid.UUID(units[0]["id"]))
        assert unit.status == "missing" and unit.location_code is None
    line["quantity"] = "1"
    restored = operation(client, manager, "adjustment", [line])
    assert restored.status_code == 200, restored.text
    with Session(application.state.engine) as db:
        unit = db.get(EquipmentSerial, uuid.UUID(units[0]["id"]))
        assert unit.status == "in_stock" and unit.location_code == "MAIN"
        assert db.scalar(select(func.sum(StockLedger.quantity_delta))) == 1


def test_unidentified_hardware_cannot_allocate_or_bypass_order_dispatch(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    headers = _warehouse(client)
    _receipt_validate(client, headers, "PANEL-550", "6")
    allocation = client.post(
        "/api/v1/stock/allocations",
        json={
            "order_id": order["id"],
            "lines": [{"component_code": "PANEL-550", "location_code": "MAIN", "quantity": 1}],
        },
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert allocation.status_code == 409
    assert allocation.json()["error"]["code"] == "serial_registration_required"
    bypass = operation(
        client,
        headers,
        "delivery",
        [{"component_code": "PANEL-550", "quantity": "1", "from_location": "MAIN"}],
    )
    assert bypass.status_code == 409
    assert bypass.json()["error"]["code"] == "use_order_fulfilment"


def test_duplicate_lines_cannot_hide_known_untracked_identity(client, application):
    _all_staff(application)
    headers = _warehouse(client)
    receipt = _receipt_validate(client, headers, "CONN-MC4", "10")
    scanned = client.post(
        "/api/v1/serials/scan",
        json={
            "serial_number": "TEST-KNOWN-CONNECTOR",
            "component_code": "CONN-MC4",
            "operation_id": receipt["id"],
        },
        headers=headers,
    )
    assert scanned.status_code == 201
    line = {
        "component_code": "CONN-MC4",
        "quantity": "5",
        "from_location": "MAIN",
        "to_location": "SITE",
    }
    result = operation(client, headers, "transfer", [line, line])
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "serials_required"
    with Session(application.state.engine) as db:
        assert db.get(EquipmentSerial, uuid.UUID(scanned.json()["id"])).location_code == "MAIN"
        assert db.scalar(select(func.sum(StockLedger.quantity_delta))) == 10


@pytest.mark.parametrize(
    "case,code",
    [
        ("fraction", "serialized_quantity"),
        ("too-many", "serial_quantity_mismatch"),
        ("wrong-component", "serial_component_mismatch"),
        ("quarantine", "quarantine_blocked"),
        ("duplicate", "duplicate_serial"),
        ("receipt-identity", "receipt_serial_registration"),
    ],
)
def test_invalid_identity_movements_fail_without_ledger_or_unit_change(
    client, application, case, code
):
    headers, units = received(client, application)
    line = {
        "component_code": "PANEL-550",
        "quantity": "1",
        "from_location": "MAIN",
        "to_location": "SITE",
        "serial_ids": [units[0]["id"]],
    }
    kind = "transfer"
    if case == "fraction":
        line["quantity"] = "0.5"
    if case == "too-many":
        # An untracked component can still have explicit known identities.
        line["component_code"] = "CONN-MC4"
        receipt = _receipt_validate(client, headers, "CONN-MC4", "2")
        ids = []
        for index in range(2):
            result = client.post(
                "/api/v1/serials/scan",
                json={
                    "serial_number": f"TEST-CONN-{index}",
                    "component_code": "CONN-MC4",
                    "operation_id": receipt["id"],
                },
                headers=headers,
            )
            assert result.status_code == 201
            ids.append(result.json()["id"])
        line["serial_ids"] = ids
    if case == "wrong-component":
        line["component_code"] = "CONN-MC4"
    if case == "quarantine":
        _receipt_validate(client, headers, "PANEL-550", "1", "QUARANTINE")
        line["from_location"] = "QUARANTINE"
        line["to_location"] = "MAIN"
    if case == "duplicate":
        line["serial_ids"] *= 2
    if case == "receipt-identity":
        kind = "receipt"
        line.pop("from_location")
    with Session(application.state.engine) as db:
        before = db.scalar(select(func.count()).select_from(StockLedger))
    created = client.post(
        "/api/v1/stock/operations",
        json={"operation_type": kind, "lines": [line]},
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    if created.status_code == 201:
        oid = created.json()["id"]
        assert (
            client.post(f"/api/v1/stock/operations/{oid}/ready", headers=headers).status_code == 200
        )
        result = client.post(f"/api/v1/stock/operations/{oid}/validate", headers=headers)
    else:
        result = created
    assert result.status_code in {409, 422}, result.text
    assert result.json()["error"]["code"] == code
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(StockLedger)) == before
        assert db.get(EquipmentSerial, uuid.UUID(units[0]["id"])).location_code == "MAIN"
