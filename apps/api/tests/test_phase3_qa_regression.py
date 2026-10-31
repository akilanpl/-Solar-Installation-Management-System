"""Independent Phase 3 API regressions; failures document product defects."""

import uuid
from datetime import UTC, datetime

import pytest
from app.models.identity import User
from app.models.phase3 import (
    Delivery,
    InstallationJob,
    InstallationOtp,
    StockLedger,
    StockOperation,
)
from app.services.inventory_service import threshold_suggestion
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.test_phase3_warehouse_installation import (
    _all_staff,
    _confirmed_order,
    _customer,
    _order_material,
    _receipt_material,
    _receipt_validate,
    _sales,
    _technician,
    _warehouse,
)

pytestmark = pytest.mark.database


def _job(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    with Session(application.state.engine) as db:
        technician_id = db.scalar(select(User.id).where(User.email == "tech@example.com"))
    response = client.post(
        "/api/v1/jobs",
        json={"order_id": order["id"], "technician_user_id": str(technician_id)},
        headers=_sales(client),
    )
    assert response.status_code == 201
    return response.json(), order


@pytest.mark.parametrize("path", ["/stock", "/stock/reservations", "/deliveries", "/jobs"])
def test_phase3_anonymous_reads_require_authentication(client, path):
    response = client.get(f"/api/v1{path}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


@pytest.mark.parametrize("path", ["/stock/operations", "/serials/scan", "/deliveries", "/jobs"])
def test_phase3_mutations_enforce_csrf_before_business_operations(client, path):
    response = client.post(f"/api/v1{path}", json={})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


@pytest.mark.parametrize(
    "patch,status",
    [
        ({"quantity": "0"}, 400),
        ({"quantity": "-1"}, 400),
        ({"component_code": "UNKNOWN-COMPONENT"}, 400),
        ({"to_location": "UNKNOWN-LOCATION"}, 400),
        ({"to_location": None}, 400),
    ],
)
def test_invalid_stock_creation_rolls_back_header_lines_and_ledger(
    client, application, patch, status
):
    _all_staff(application)
    warehouse = _warehouse(client)
    line = {"component_code": "PANEL-550", "quantity": "2", "to_location": "MAIN", **patch}
    response = client.post(
        "/api/v1/stock/operations",
        json={"operation_type": "receipt", "lines": [line]},
        headers={**warehouse, "Idempotency-Key": "qa-invalid-stock"},
    )
    assert response.status_code == status
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(StockOperation)) == 0
        assert db.scalar(select(func.count()).select_from(StockLedger)) == 0


def test_stock_mass_assignment_and_bad_uuid_are_rejected(client, application):
    _all_staff(application)
    warehouse = _warehouse(client)
    response = client.post(
        "/api/v1/stock/operations",
        json={
            "operation_type": "receipt",
            "status": "done",
            "lines": [{"component_code": "PANEL-550", "quantity": "2", "to_location": "MAIN"}],
        },
        headers={**warehouse, "Idempotency-Key": "qa-mass-assignment"},
    )
    assert response.status_code == 422
    assert client.get("/api/v1/stock/operations/not-a-uuid").status_code == 422
    assert client.get(f"/api/v1/stock/operations/{uuid.uuid4()}").status_code == 404
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(StockOperation)) == 0


def test_replenishment_suggestion_uses_ledger_minus_reserved_without_writes(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    material = dict(_order_material(application, order["id"]))
    reserved = material["PANEL-550"]
    _receipt_validate(client, _warehouse(client), "PANEL-550", str(reserved + 5))
    with Session(application.state.engine) as db:
        before = db.scalar(select(func.count()).select_from(StockLedger))
        suggestion = threshold_suggestion(db, "PANEL-550", threshold=10)
        assert suggestion == {
            "component_code": "PANEL-550",
            "on_hand": reserved + 5,
            "reserved": reserved,
            "available": 5,
            "below_threshold": True,
            "suggested_quantity": 15,
        }
        assert db.scalar(select(func.count()).select_from(StockLedger)) == before


def test_delivery_retry_replays_without_second_pick_and_changed_body_conflicts(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    warehouse = _warehouse(client)
    _receipt_material(client, warehouse, _order_material(application, order["id"]))
    headers = {**warehouse, "Idempotency-Key": "qa-delivery-retry"}
    first = client.post("/api/v1/deliveries", json={"order_id": order["id"]}, headers=headers)
    assert first.status_code == 201
    with Session(application.state.engine) as db:
        count = db.scalar(select(func.count()).select_from(StockLedger))
    replay = client.post("/api/v1/deliveries", json={"order_id": order["id"]}, headers=headers)
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]
    other_order = _confirmed_order(client, application, "second-delivery@example.com")
    headers = {**_warehouse(client), "Idempotency-Key": "qa-delivery-retry"}
    conflict = client.post(
        "/api/v1/deliveries", json={"order_id": other_order["id"]}, headers=headers
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Delivery)) == 1
        assert db.scalar(select(func.count()).select_from(StockLedger)) == count


def test_foreign_customer_cannot_read_or_list_job_and_job_get_does_not_repeat_code(
    client, application
):
    job, _order = _job(client, application)
    assert client.get(f"/api/v1/jobs/{job['id']}").json()["customer_code"] is None
    _customer(client, application, "outsider@example.com")
    assert client.get(f"/api/v1/jobs/{job['id']}").status_code == 404
    assert client.get("/api/v1/jobs").json() == []


def test_delivery_and_warranty_are_hidden_from_a_different_customer(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    warehouse = _warehouse(client)
    _receipt_material(client, warehouse, _order_material(application, order["id"]))
    created = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={
            **warehouse,
            "Idempotency-Key": "qa-delivery-ownership",
        },
    )
    assert created.status_code == 201
    delivery_id = created.json()["id"]
    for action in ("transit", "deliver", "confirm"):
        assert (
            client.post(f"/api/v1/deliveries/{delivery_id}/{action}", headers=warehouse).status_code
            == 200
        )
    _customer(client, application, "warranty-outsider@example.com")
    assert client.get(f"/api/v1/deliveries/{delivery_id}").status_code == 404
    assert client.get("/api/v1/deliveries").json() == []
    assert client.get(f"/api/v1/warranties/order/{order['id']}").status_code == 404


def test_customer_otp_wrong_attempts_persist_and_lock_after_five(client, application):
    job, _order = _job(client, application)
    headers = _technician(client)
    for _ in range(5):
        response = client.post(
            f"/api/v1/jobs/{job['id']}/customer-otp", json={"code": "000000"}, headers=headers
        )
        assert response.status_code == 400
    with Session(application.state.engine) as db:
        attempts = db.scalar(
            select(InstallationOtp.attempt_count).where(
                InstallationOtp.job_id == uuid.UUID(job["id"])
            )
        )
    sixth = client.post(
        f"/api/v1/jobs/{job['id']}/customer-otp", json={"code": "000000"}, headers=headers
    )
    # Only non-secret diagnostics appear when this assertion fails.
    actual = (attempts, sixth.status_code, sixth.json()["error"]["code"])
    assert actual == (5, 409, "otp_locked")


def test_inactive_technician_cannot_be_assigned_to_a_new_job(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    with Session(application.state.engine) as db:
        technician = db.scalar(select(User).where(User.email == "tech@example.com"))
        technician.is_active = False
        technician_id = str(technician.id)
        db.commit()
    response = client.post(
        "/api/v1/jobs",
        json={
            "order_id": order["id"],
            "technician_user_id": technician_id,
        },
        headers=_sales(client),
    )
    assert response.status_code == 400
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(InstallationJob)) == 0


def test_completion_requires_recorded_arrival_even_after_otp_evidence_and_signature(
    client, application
):
    job, _order = _job(client, application)
    headers = _technician(client)
    verified = client.post(
        f"/api/v1/jobs/{job['id']}/customer-otp",
        json={"code": job["customer_code"]},
        headers=headers,
    )
    assert verified.status_code == 200
    now = datetime.now(UTC).isoformat()
    evidence = client.post(
        f"/api/v1/jobs/{job['id']}/evidence",
        json={
            "photo_refs": ["QA-PHOTO-1"],
            "started_at": now,
            "finished_at": now,
        },
        headers=headers,
    )
    assert evidence.status_code == 200
    signature = client.post(
        f"/api/v1/jobs/{job['id']}/signature",
        json={
            "signature_ref": "QA-SIGNATURE-1",
            "customer_confirmed": True,
        },
        headers=headers,
    )
    assert signature.status_code == 200
    completed = client.post(f"/api/v1/jobs/{job['id']}/completion", headers=headers)
    with Session(application.state.engine) as db:
        saved = db.get(InstallationJob, uuid.UUID(job["id"]))
        actual = (completed.status_code, saved.status, saved.arrival_at is not None)
    assert actual == (409, "en_route", False)
