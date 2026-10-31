"""Phase 4B warranty-aware replacement with real warehouse custody."""

import uuid

import pytest
from app.models.phase3 import EquipmentSerial, StockLedger
from app.models.warranty import SerializedAssetCoverage
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase4a_support import (
    _all_staff,
    _create_ticket,
    _installed_order,
    _login,
    _repair_job,
    _support,
    _tech_id,
    _technician,
    _technician2,
    _triage,
    _warehouse,
)
from tests.test_phase4b_warranty import _admin, _decide, _policy

pytestmark = pytest.mark.database


def _covered_ticket(client, application, serial_new="SN-RPL-0001", **policy_kw):
    admin = _admin(client, application)
    _policy(client, admin, **policy_kw)
    order, serial = _installed_order(client, application)
    warehouse = _warehouse(client)
    from tests.test_phase4a_support import _order_material, _receipt_validate

    component = _order_material(application, order["id"])[0][0]
    receipt = _receipt_validate(client, warehouse, component, "1.0000", "MAIN")
    scanned = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": serial_new, "component_code": component,
              "operation_id": receipt["id"]},
        headers=warehouse,
    )
    assert scanned.status_code == 201, scanned.text
    support = _support(client)
    assert client.post(f"/api/v1/warranty/orders/{order['id']}/activate-coverages",
                       headers=support).status_code == 201
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    _triage(client, ticket["id"])
    decided = _decide(client, _support(client), ticket["id"], serial)
    assert decided.json()["verdict"] == "covered", decided.text
    return ticket, serial, serial_new, order


def _propose(client, ticket_id, old, new, key=None):
    return client.post(
        "/api/v1/replacements",
        json={"ticket_id": ticket_id, "old_serial_number": old, "new_serial_number": new},
        headers={**_support(client), "Idempotency-Key": key or uuid.uuid4().hex},
    )


def _ledger_total(application, component):
    with Session(application.state.engine) as db:
        return db.scalar(
            select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
                StockLedger.component_code == component,
                StockLedger.location_code == "MAIN")
        )


def _serial_status(application, serial_number):
    with Session(application.state.engine) as db:
        row = db.scalar(select(EquipmentSerial).where(
            func.lower(EquipmentSerial.serial_number) == serial_number.lower()))
        assert row is not None
        return row.status


def _submit_acknowledged_swap(client, application, ticket, old, new, job=None):
    from datetime import UTC, datetime, timedelta

    from tests.test_phase3_warehouse_installation import _png

    job = job or _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    tech = _technician(client)
    path = f"/api/v1/repair-jobs/{job['id']}"
    arrived = client.post(path + "/arrival", headers=tech)
    assert arrived.status_code == 200, arrived.text
    diagnostics = client.post(path + "/diagnostics", json={
        "findings": f"Original {old} defective; replacement {new} matched.",
        "root_cause": "Verified defective component",
    }, headers=tech)
    assert diagnostics.status_code == 200, diagnostics.text
    evidence = client.post(f"/api/v1/tickets/{ticket['id']}/attachments",
        params={"repair_job_id": job["id"]},
        files={"upload": ("swap.png", _png(), "image/png")}, headers=tech)
    assert evidence.status_code == 201, evidence.text
    now = datetime.now(UTC)
    work = client.post(path + "/work", json={
        "work_performed": f"Removed {old}; installed {new}; tested electrical continuity.",
        "work_started_at": (now - timedelta(minutes=1)).isoformat(),
        "work_finished_at": now.isoformat(), "parts_used": [],
    }, headers=tech)
    assert work.status_code == 200, work.text
    submitted = client.post(path + "/submit", json={
        "summary": f"Replacement {new} installed and original {old} retained for return.",
    }, headers=tech)
    assert submitted.status_code == 200, submitted.text
    ready = client.post(f"/api/v1/tickets/{ticket['id']}/resolution-ready", json={
        "summary": f"Exact replacement {new} installed for {old}; customer to review.",
    }, headers=_support(client))
    assert ready.status_code == 200, ready.text
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    confirmation = client.post(f"/api/v1/tickets/{ticket['id']}/confirmation", json={
        "decision": "confirmed", "summary_version": ready.json()["resolution_version"],
    }, headers=customer)
    assert confirmation.status_code == 200, confirmation.text
    return job


def test_replacement_full_custody_and_transfer(client, application):
    from tests.test_phase4a_support import _order_material

    _all_staff(application)
    ticket, old, new, order = _covered_ticket(client, application)
    component = _order_material(application, order["id"])[0][0]
    before = _ledger_total(application, component)
    proposed = _propose(client, ticket["id"], old, new)
    assert proposed.status_code == 201, proposed.text
    body = proposed.json()
    assert body["status"] == "proposed"
    assert body["manufacturer_status"] == "not_required"
    replacement_id = body["id"]
    support = _support(client)
    approved = client.post(f"/api/v1/replacements/{replacement_id}/approve", headers=support)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert _serial_status(application, old) == "faulty"
    warehouse = _warehouse(client)
    reserved = client.post(f"/api/v1/replacements/{replacement_id}/reserve", headers=warehouse)
    assert reserved.status_code == 200, reserved.text
    assert _serial_status(application, new) == "reserved"
    issued = client.post(
        f"/api/v1/replacements/{replacement_id}/issue",
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex})
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "issued"
    assert _ledger_total(application, component) == before - 1
    assert _serial_status(application, new) == "in_transit"
    assert _serial_status(application, old) == "faulty"
    with Session(application.state.engine) as db:
        from app.models.custody import StockSerialMovement
        from app.models.phase3 import StockOperation

        operation = db.get(StockOperation, uuid.UUID(issued.json()["issue_operation_id"]))
        movements = list(db.scalars(select(StockSerialMovement).where(
            StockSerialMovement.operation_id == operation.id)))
        assert operation.status == "done"
        assert len(movements) == 1 and movements[0].serial_number == new
        assert db.scalar(select(SerializedAssetCoverage).where(
            SerializedAssetCoverage.serial_id == movements[0].serial_id)) is None
    replay = client.post(
        f"/api/v1/replacements/{replacement_id}/issue",
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex})
    assert replay.status_code == 200, replay.text
    premature = client.post(
        f"/api/v1/replacements/{replacement_id}/install", headers=_support(client))
    assert premature.status_code == 409, premature.text
    assert premature.json()["error"]["code"] == "installation_evidence_required"
    _submit_acknowledged_swap(client, application, ticket, old, new)
    installed = client.post(
        f"/api/v1/replacements/{replacement_id}/install", headers=_support(client))
    assert installed.status_code == 200, installed.text
    assert installed.json()["status"] == "installed"
    with Session(application.state.engine) as db:
        old_coverage = db.scalar(select(SerializedAssetCoverage).where(
            SerializedAssetCoverage.serial_id == db.scalar(select(EquipmentSerial.id).where(
                func.lower(EquipmentSerial.serial_number) == old.lower()))))
        assert old_coverage is not None and old_coverage.status == "superseded"
        new_serial_id = db.scalar(select(EquipmentSerial.id).where(
            func.lower(EquipmentSerial.serial_number) == new.lower()))
        new_coverage = db.scalar(select(SerializedAssetCoverage).where(
            SerializedAssetCoverage.serial_id == new_serial_id))
        assert new_coverage is not None and new_coverage.status == "active"
        assert new_coverage.ends_at == old_coverage.ends_at
        assert new_coverage.supersedes_coverage_id == old_coverage.id
    warehouse = _warehouse(client)
    inspected = client.post(
        f"/api/v1/replacements/{replacement_id}/inspect",
        json={"verdict": "restocked",
              "note": "Isolator board replaced on the bench; unit tests clean."},
        headers=warehouse,
    )
    assert inspected.status_code == 201, inspected.text
    assert _serial_status(application, old) == "in_stock"
    assert _ledger_total(application, component) == before


def test_manufacturer_gate_blocks_issue(client, application):
    _all_staff(application)
    ticket, old, new, _ = _covered_ticket(
        client, application, serial_new="SN-RPL-0002", manufacturer_auth_required=True)
    proposed = _propose(client, ticket["id"], old, new)
    assert proposed.status_code == 201, proposed.text
    replacement_id = proposed.json()["id"]
    approved = client.post(
        f"/api/v1/replacements/{replacement_id}/approve", headers=_support(client))
    assert approved.json()["status"] == "pending_manufacturer"
    assert approved.json()["manufacturer_status"] == "pending"
    warehouse = _warehouse(client)
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/reserve", headers=warehouse).status_code == 409
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/issue",
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex}).status_code == 409
    empty = client.post(
        f"/api/v1/replacements/{replacement_id}/manufacturer-auth",
        json={"evidence_ref": ""}, headers=_support(client))
    assert empty.status_code == 422, empty.text
    authorized = client.post(
        f"/api/v1/replacements/{replacement_id}/manufacturer-auth",
        json={"evidence_ref": "MFR-RMA-2026-1187 confirmation letter on file."},
        headers=_support(client))
    assert authorized.status_code == 200, authorized.text
    assert authorized.json()["status"] == "approved"
    assert authorized.json()["manufacturer_status"] == "approved"


def test_replacement_guards(client, application):
    _all_staff(application)
    ticket, old, new, _ = _covered_ticket(client, application, serial_new="SN-RPL-0003")
    support = _support(client)
    assert client.post(
        "/api/v1/replacements",
        json={"ticket_id": ticket["id"], "old_serial_number": old,
              "new_serial_number": "SN-NOPE-1"},
        headers={**support, "Idempotency-Key": uuid.uuid4().hex},
    ).status_code == 404
    wrong_component = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": "SN-RPL-OTHER", "component_code": "INV-5K"},
        headers=_warehouse(client),
    )
    if wrong_component.status_code == 201:
        mismatch = _propose(client, ticket["id"], old, "SN-RPL-OTHER")
        assert mismatch.status_code in (404, 422), mismatch.text
    key = uuid.uuid4().hex
    first = _propose(client, ticket["id"], old, new, key=key)
    assert first.status_code == 201, first.text
    replay = _propose(client, ticket["id"], old, new, key=key)
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == first.json()["id"]
    second_new = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": "SN-RPL-0004", "component_code": "PANEL-550"},
        headers=_warehouse(client),
    )
    assert second_new.status_code in (201, 404, 422)
    claimed = _propose(client, ticket["id"], old, new)
    assert claimed.status_code == 409, claimed.text
    assert claimed.json()["error"]["code"] == "replacement_exists"
    cancelled = client.post(
        f"/api/v1/replacements/{first.json()['id']}/cancel",
        json={"reason": "Customer chose a repair instead."},
        headers=_support(client),
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    early_inspect = client.post(
        f"/api/v1/replacements/{first.json()['id']}/inspect",
        json={"verdict": "quarantined", "note": "Nothing returned yet at all."},
        headers=_warehouse(client),
    )
    assert early_inspect.status_code == 409, early_inspect.text


def test_replacement_roles_and_quarantine(client, application):
    _all_staff(application)
    ticket, old, new, _ = _covered_ticket(client, application, serial_new="SN-RPL-0005")
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    assert client.post(
        "/api/v1/replacements",
        json={"ticket_id": ticket["id"], "old_serial_number": old, "new_serial_number": new},
        headers={**customer, "Idempotency-Key": uuid.uuid4().hex},
    ).status_code == 403
    proposed = _propose(client, ticket["id"], old, new)
    replacement_id = proposed.json()["id"]
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/reserve",
        headers=_support(client)).status_code == 403
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/approve",
        headers=_warehouse(client)).status_code == 403
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/approve", headers=_support(client)).status_code == 200
    warehouse = _warehouse(client)
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/reserve", headers=warehouse).status_code == 200
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/issue",
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex}).status_code == 200
    early = client.post(f"/api/v1/replacements/{replacement_id}/inspect",
        json={"verdict": "quarantined", "note": "Cannot receive before physical swap."},
        headers=warehouse)
    assert early.status_code == 409, early.text
    _submit_acknowledged_swap(client, application, ticket, old, new)
    installed = client.post(f"/api/v1/replacements/{replacement_id}/install", headers=_support(client))
    assert installed.status_code == 200, installed.text
    warehouse = _warehouse(client)
    quarantined = client.post(
        f"/api/v1/replacements/{replacement_id}/inspect",
        json={"verdict": "quarantined",
              "note": "Burn marks on the control board; hold for manufacturer review."},
        headers=warehouse,
    )
    assert quarantined.status_code == 201, quarantined.text
    assert _serial_status(application, old) == "quarantined"
    again = client.post(
        f"/api/v1/replacements/{replacement_id}/inspect",
        json={"verdict": "restocked", "note": "Trying to inspect the same return twice."},
        headers=warehouse,
    )
    assert again.status_code == 409, again.text


def test_technician_confirms_install_and_fixed_days(client, application):
    _all_staff(application)
    ticket, old, new, _ = _covered_ticket(
        client, application, serial_new="SN-RPL-0006",
        replacement_continuation="fixed_days", replacement_warranty_days=90)
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    assert job["technician_user_id"] == _tech_id(application, "tech@example.com")
    proposed = _propose(client, ticket["id"], old, new)
    replacement_id = proposed.json()["id"]
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/approve", headers=_support(client)).status_code == 200
    warehouse = _warehouse(client)
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/reserve", headers=warehouse).status_code == 200
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/issue",
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex}).status_code == 200
    _submit_acknowledged_swap(client, application, ticket, old, new, job=job)
    technician = _technician(client)
    installed = client.post(
        f"/api/v1/replacements/{replacement_id}/install", headers=technician)
    assert installed.status_code == 200, installed.text
    stranger = _technician2(client)
    assert client.post(
        f"/api/v1/replacements/{replacement_id}/install", headers=stranger).status_code in (404, 409)
    with Session(application.state.engine) as db:
        new_serial_id = db.scalar(select(EquipmentSerial.id).where(
            func.lower(EquipmentSerial.serial_number) == new.lower()))
        new_coverage = db.scalar(select(SerializedAssetCoverage).where(
            SerializedAssetCoverage.serial_id == new_serial_id))
        assert new_coverage is not None
        span = new_coverage.ends_at - new_coverage.starts_at
        assert span.days == 90, span
