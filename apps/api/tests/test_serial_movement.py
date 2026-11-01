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


def test_a_returned_unit_can_have_a_new_custody_episode_without_erasing_old_delivery(
    client, application
):
    from app.models.custody import StockSerialMovement
    from tests.test_location_fulfilment import _finish, _post

    _all_staff(application)
    first = _confirmed_order(client, application, email="first-custody@example.com")
    headers = _warehouse(client)
    receipt = _receipt_validate(client, headers, "PANEL-550", "6")
    units = _register_received_units(client, headers, receipt, "PANEL-550")
    unit = units[0]
    assert (
        client.post(
            f"/api/v1/serials/{unit['id']}/assign", json={"order_id": first["id"]}, headers=headers
        ).status_code
        == 200
    )

    def pick(order_id):
        result = _post(
            client,
            "/deliveries",
            {
                "order_id": order_id,
                "lines": [{"component_code": "PANEL-550", "location_code": "MAIN", "quantity": 1}],
            },
            _warehouse(client),
        )
        assert result.status_code == 201, result.text
        delivery = result.json()
        assert delivery["lines"][0]["serial_numbers"] == [unit["serial_number"]]
        _finish(client, delivery, _warehouse(client))
        return delivery

    def return_unit(delivery):
        result = _post(
            client,
            "/stock/returns",
            {
                "delivery_line_id": delivery["lines"][0]["id"],
                "quantity": 1,
                "serial_id": unit["id"],
                "reason": "Test usable unit return",
            },
            _warehouse(client),
        )
        assert result.status_code == 200, result.text
        inspected = _post(
            client,
            f"/stock/returns/{result.json()['id']}/inspection",
            {"disposition": "restock", "note": "Test fixture inspected usable"},
            _manager(client),
        )
        assert inspected.status_code == 200, inspected.text

    original = pick(first["id"])
    # A carrier has the unit after dispatch; no automatic ledger restock is allowed.
    return_unit(original)
    second = _confirmed_order(client, application, email="second-custody@example.com")
    headers = _warehouse(client)
    assigned = client.post(
        f"/api/v1/serials/{unit['id']}/assign", json={"order_id": second["id"]}, headers=headers
    )
    assert assigned.status_code == 200, assigned.text
    later = pick(second["id"])
    return_unit(later)
    old = client.get(f"/api/v1/deliveries/{original['id']}", headers=_warehouse(client))
    assert old.status_code == 200
    assert old.json()["lines"][0]["serial_numbers"] == [unit["serial_number"]]
    with Session(application.state.engine) as db:
        row = db.get(EquipmentSerial, uuid.UUID(unit["id"]))
        assert row.status == "in_stock" and row.order_id is None and row.delivery_line_id is None
        history = list(
            db.scalars(select(StockSerialMovement).where(StockSerialMovement.serial_id == row.id))
        )
        assert len(history) == 5  # receipt, first pick/return, second pick/return
        assert {str(item.delivery_line_id) for item in history if item.delivery_line_id} == {
            original["lines"][0]["id"],
            later["lines"][0]["id"],
        }


def test_dispatched_goods_cannot_be_auto_restocked_by_cancellation(client, application):
    from tests.test_phase3_warehouse_installation import _order_material, _receipt_material

    _all_staff(application)
    order = _confirmed_order(client, application)
    headers = _warehouse(client)
    _receipt_material(client, headers, _order_material(application, order["id"]))
    delivery = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    ).json()
    assert (
        client.post(f"/api/v1/deliveries/{delivery['id']}/transit", headers=headers).status_code
        == 200
    )
    with Session(application.state.engine) as db:
        before = db.scalar(select(func.count()).select_from(StockLedger))
    denied = client.post(f"/api/v1/deliveries/{delivery['id']}/cancel", headers=headers)
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "invalid_transition"
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(StockLedger)) == before
        assert all(unit.status == "in_transit" for unit in db.scalars(select(EquipmentSerial)))


def test_positive_count_correction_cannot_invent_another_copy_of_a_present_unit(
    client, application
):
    headers, units = received(client, application, 1)
    manager = _manager(client)
    line = {
        "component_code": "PANEL-550",
        "quantity": "1",
        "to_location": "MAIN",
        "serial_ids": [units[0]["id"]],
    }
    result = operation(client, manager, "adjustment", [line])
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "invalid_serial_state"
    for reason in (None, "x"):
        result = client.post(
            "/api/v1/stock/operations",
            json={"operation_type": "adjustment", "lines": [line], "note": reason},
            headers={**manager, "Idempotency-Key": uuid.uuid4().hex},
        )
        assert result.status_code == 403
        assert result.json()["error"]["code"] == "adjustment_approval_required"
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.sum(StockLedger.quantity_delta))) == 1
        assert db.get(EquipmentSerial, uuid.UUID(units[0]["id"])).status == "in_stock"
