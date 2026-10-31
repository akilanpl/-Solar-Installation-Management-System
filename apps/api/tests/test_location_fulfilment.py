"""Persistent Phase 3 custody tests: partial picks, allocations, returns and supply."""

import uuid

import pytest
from app.models.operations import StockAllocation
from app.models.phase3 import StockLedger, StockReservation, Warranty
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import (
    _all_staff,
    _confirmed_order,
    _customer,
    _manager,
    _order_material,
    _receipt_validate,
    _warehouse,
)

pytestmark = pytest.mark.database


def _post(client, path, data, headers, key=None):
    return client.post(
        "/api/v1" + path, json=data, headers={**headers, "Idempotency-Key": key or uuid.uuid4().hex}
    )


def _setup(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    return order, dict(_order_material(application, order["id"])), _warehouse(client)


def _finish(client, delivery, headers):
    for action in ["transit", "deliver", "confirm"]:
        result = _post(client, f"/deliveries/{delivery['id']}/{action}", None, headers)
        assert result.status_code == 200, result.text


def test_partial_multi_location_pick_confirm_cancel_and_retry(client, application):
    order, materials, wh = _setup(client, application)
    for code, qty in materials.items():
        _receipt_validate(client, wh, code, str(qty), "SITE")
    code = next(iter(materials))
    body = {
        "order_id": order["id"],
        "lines": [{"component_code": code, "location_code": "SITE", "quantity": 1}],
    }
    first = _post(client, "/deliveries", body, wh, "partial-first")
    assert first.status_code == 201, first.text
    assert (
        _post(client, "/deliveries", body, wh, "partial-first").json()["id"] == first.json()["id"]
    )
    _finish(client, first.json(), wh)
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Warranty)) == 0
        assert all(r.status == "reserved" for r in db.scalars(select(StockReservation)))
    final = _post(client, "/deliveries", {"order_id": order["id"]}, wh)
    assert final.status_code == 201, final.text
    assert all(line["location_code"] == "SITE" for line in final.json()["lines"])
    cancelled = _post(client, f"/deliveries/{final.json()['id']}/cancel", None, wh)
    assert cancelled.status_code == 200, cancelled.text
    replacement = _post(client, "/deliveries", {"order_id": order["id"]}, wh)
    assert replacement.status_code == 201, replacement.text
    _finish(client, replacement.json(), wh)
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Warranty)) == 1
        assert all(r.status == "consumed" for r in db.scalars(select(StockReservation)))
        assert db.scalar(select(func.sum(StockLedger.quantity_delta))) == 0
    assert _post(client, "/deliveries", {"order_id": order["id"]}, wh).status_code == 409


def test_location_allocation_is_idempotent_and_blocks_transfer(client, application):
    order, materials, wh = _setup(client, application)
    code, qty = next(iter(materials.items()))
    _receipt_validate(client, wh, code, str(qty), "SITE")
    payload = {
        "order_id": order["id"],
        "lines": [{"component_code": code, "location_code": "SITE", "quantity": qty}],
    }
    for _ in range(2):
        result = _post(client, "/stock/allocations", payload, wh)
        assert result.status_code == 200, result.text
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.sum(StockAllocation.quantity))) == qty
    move = _post(
        client,
        "/stock/operations",
        {
            "operation_type": "transfer",
            "lines": [
                {
                    "component_code": code,
                    "quantity": str(qty),
                    "from_location": "SITE",
                    "to_location": "MAIN",
                }
            ],
        },
        wh,
    )
    oid = move.json()["id"]
    assert _post(client, f"/stock/operations/{oid}/ready", None, wh).status_code == 200
    assert _post(client, f"/stock/operations/{oid}/validate", None, wh).status_code == 409
    pick = _post(
        client,
        "/deliveries",
        {
            "order_id": order["id"],
            "lines": [{"component_code": code, "location_code": "SITE", "quantity": qty}],
        },
        wh,
    )
    assert pick.status_code == 201, pick.text
    assert _post(client, f"/deliveries/{pick.json()['id']}/cancel", None, wh).status_code == 200
    with Session(application.state.engine) as db:
        assert db.scalar(select(StockAllocation.picked_quantity)) == 0


@pytest.mark.parametrize("disposition,location", [("damaged", "QUARANTINE"), ("restock", "SITE")])
def test_inspected_return_compensates_once_and_enforces_role(
    client, application, disposition, location
):
    order, materials, wh = _setup(client, application)
    code = next(iter(materials))
    _receipt_validate(client, wh, code, "1", "SITE")
    picked = _post(
        client,
        "/deliveries",
        {
            "order_id": order["id"],
            "lines": [{"component_code": code, "location_code": "SITE", "quantity": 1}],
        },
        wh,
    ).json()
    _finish(client, picked, wh)
    payload = {
        "delivery_line_id": picked["lines"][0]["id"],
        "quantity": 1,
        "reason": "Test inspection fixture",
    }
    authorized = _post(client, "/stock/returns", payload, wh, "return-once")
    assert authorized.status_code == 200, authorized.text
    rid = authorized.json()["id"]
    assert _post(client, "/stock/returns", payload, wh, "return-once").json()["id"] == rid
    assert _post(client, "/stock/returns", payload, wh).status_code == 409
    inspection = {"disposition": disposition, "note": "Inspected isolated fixture"}
    assert _post(client, f"/stock/returns/{rid}/inspection", inspection, wh).status_code == 403
    manager = _manager(client)
    done = _post(client, f"/stock/returns/{rid}/inspection", inspection, manager)
    assert done.status_code == 200, done.text
    assert _post(client, f"/stock/returns/{rid}/inspection", inspection, manager).status_code == 409
    with Session(application.state.engine) as db:
        assert (
            db.scalar(
                select(func.sum(StockLedger.quantity_delta)).where(
                    StockLedger.location_code == location, StockLedger.component_code == code
                )
            )
            == 1
        )


def test_supplier_chain_requires_approval_and_matching_validated_receipt(client, application):
    _all_staff(application)
    wh = _warehouse(client)
    req = _post(
        client,
        "/replenishment/requests",
        {"component_code": "PANEL-550", "location_code": "SITE", "quantity": 2},
        wh,
    ).json()
    payload = {
        "replenishment_request_id": req["id"],
        "supplier_name": "Isolated supplier fixture",
        "supplier_reference": "TEST-DOCUMENT-1",
    }
    assert _post(client, "/procurement/orders", payload, wh).status_code == 403
    manager = _manager(client)
    assert _post(client, "/procurement/orders", payload, manager).status_code == 409
    assert (
        _post(
            client,
            f"/replenishment/requests/{req['id']}/decision",
            {"decision": "approve"},
            manager,
        ).status_code
        == 200
    )
    supplier = _post(client, "/procurement/orders", payload, manager)
    assert supplier.status_code == 200, supplier.text
    sid = supplier.json()["id"]
    wrong = _receipt_validate(client, manager, "PANEL-550", "1", "SITE")
    assert (
        _post(
            client, f"/procurement/orders/{sid}/receipt", {"operation_id": wrong["id"]}, manager
        ).status_code
        == 409
    )
    receipt = _receipt_validate(client, manager, "PANEL-550", "2", "SITE")
    linked = _post(
        client, f"/procurement/orders/{sid}/receipt", {"operation_id": receipt["id"]}, manager
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["status"] == "received"
    assert (
        _post(
            client, f"/procurement/orders/{sid}/receipt", {"operation_id": receipt["id"]}, manager
        ).status_code
        == 200
    )


def test_customer_cannot_read_internal_custody_records(client, application):
    _customer(client, application)
    for path in [
        "/stock/returns",
        "/procurement/orders",
        "/stock/allocations?order_id=" + str(uuid.uuid4()),
    ]:
        assert client.get("/api/v1" + path).status_code == 403
