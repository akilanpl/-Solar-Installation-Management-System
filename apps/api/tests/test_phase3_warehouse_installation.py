"""Phase 3 warehouse, delivery, installation and warranty, against PostgreSQL."""

import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.errors import AppError
from app.core.security import hash_password, utcnow
from app.models.identity import EmployeeProfile, User
from app.models.phase3 import (
    Delivery,
    EquipmentSerial,
    InstallationJob,
    InstallationOtp,
    StockLedger,
    StockReservation,
)
from app.models.workflow import SalesOrder
from app.services.inventory_service import validate_operation
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers, login, signup_and_verify

pytestmark = pytest.mark.database

ENQUIRY = {
    "contact_name": "Leela Nair",
    "contact_phone": "9845099999",
    "contact_email": "leela@example.com",
    "site": {
        "line1": "12 Lake View Road",
        "city": "Hyderabad",
        "state": "Telangana",
        "postal_code": "500081",
    },
    "preferred_capacity_w": 3000,
    "grid_preference": "on_grid",
    "monthly_bill_minor": 450000,
    "subsidy_interest": True,
}


def _staff(application, role: str, email: str, code: str) -> None:
    with Session(application.state.engine) as db:
        user = User(
            email=email,
            password_hash=hash_password("Staffpass123"),
            role_code=role,
            email_verified_at=utcnow(),
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(
            EmployeeProfile(
                user_id=user.id,
                employee_code=code,
                full_name=role,
                phone="9845000001",
            )
        )
        db.commit()


def _login(client, kind: str, identifier: str, password: str) -> dict[str, str]:
    response = login(client, kind=kind, identifier=identifier, password=password)
    assert response.status_code == 200, response.text
    return csrf_headers(client)


def _customer(client, application, email: str = "leela@example.com") -> dict[str, str]:
    signup_and_verify(client, application, email)
    return _login(client, "customer", email, "Solarops123")


def _all_staff(application) -> None:
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    _staff(application, "warehouse_staff", "wh@example.com", "EMP-WH-901")
    _staff(application, "warehouse_manager", "whm@example.com", "EMP-WHM-901")
    _staff(application, "support", "support@example.com", "EMP-SUP-901")


def _warehouse(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-WH-901", "Staffpass123")


def _manager(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-WHM-901", "Staffpass123")


def _sales(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-SALES-901", "Staffpass123")


def _technician(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-TECH-901", "Staffpass123")


def _support(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-SUP-901", "Staffpass123")


def _enquiry(client, headers: dict[str, str]) -> dict:
    created = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    return created.json()


def _qualify(client, enquiry_id: str) -> None:
    sales = _sales(client)
    response = client.patch(
        f"/api/v1/enquiries/{enquiry_id}/qualification",
        json={"status": "under_review", "note": "Checking the roof."},
        headers=sales,
    )
    assert response.status_code == 200, response.text
    qualified = client.patch(
        f"/api/v1/enquiries/{enquiry_id}/qualification",
        json={
            "status": "qualified",
            "note": "Roof can take a 3 kW system.",
            "shadow_free_area_sqm": "40.00",
            "grid_connection_suitable": True,
        },
        headers=sales,
    )
    assert qualified.status_code == 200, qualified.text


def _survey_to_approved(client, application, enquiry_id: str) -> dict:
    sales = _sales(client)
    created = client.post("/api/v1/surveys", json={"enquiry_id": enquiry_id}, headers=sales)
    assert created.status_code == 201, created.text
    survey_id = created.json()["id"]
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        assert tech is not None
        tech_id = str(tech.id)
    assigned = client.post(
        f"/api/v1/surveys/{survey_id}/assignment",
        json={"technician_user_id": tech_id},
        headers=sales,
    )
    assert assigned.status_code == 200, assigned.text
    technician = _technician(client)
    started = client.post(f"/api/v1/surveys/{survey_id}/start", headers=technician)
    assert started.status_code == 200, started.text
    submitted = client.post(
        f"/api/v1/surveys/{survey_id}/submission",
        json={
            "azimuth_deg": "180.00",
            "tilt_deg": "12.50",
            "shadow_free_area_sqm": "38.25",
            "cable_distance_m": "25.00",
            "grid_connection": "suitable",
            "notes": "South-facing roof with a short cable run.",
        },
        headers=technician,
    )
    assert submitted.status_code == 200, submitted.text
    approved = client.post(
        f"/api/v1/surveys/{survey_id}/approval",
        json={"decision": "approved", "note": "Measurements accepted."},
        headers=_sales(client),
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


def _quote(client, survey_id: str) -> dict:
    sales = _sales(client)
    response = client.post(
        "/api/v1/quotations",
        json={"survey_id": survey_id, "package_code": "PKG-ONG-3", "discount_minor": 0},
        headers={**sales, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _confirmed_order(client, application, email: str = "leela@example.com") -> dict:
    customer = _customer(client, application, email)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    quote = _quote(client, survey["id"])
    customer = _login(client, "customer", email, "Solarops123")
    accepted = client.post(f"/api/v1/quotations/{quote['id']}/acceptance", headers=customer)
    assert accepted.status_code == 200, accepted.text
    sales = _sales(client)
    paid = client.post(
        "/api/v1/payments/cash-receipts",
        json={
            "quotation_id": quote["id"],
            "amount_minor": quote["total_minor"],
            "receipt_reference": f"CASH-{uuid.uuid4().hex[:8]}",
        },
        headers={**sales, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert paid.status_code == 201, paid.text
    created = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**_sales(client), "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    return created.json()


def _receipt_validate(
    client, headers: dict[str, str], component: str, quantity: str, location: str = "MAIN"
):
    created = client.post(
        "/api/v1/stock/operations",
        json={
            "operation_type": "receipt",
            "lines": [{"component_code": component, "quantity": quantity, "to_location": location}],
        },
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    operation_id = created.json()["id"]
    ready = client.post(f"/api/v1/stock/operations/{operation_id}/ready", headers=headers)
    assert ready.status_code == 200, ready.text
    validated = client.post(f"/api/v1/stock/operations/{operation_id}/validate", headers=headers)
    assert validated.status_code == 200, validated.text
    return validated.json()


def test_stock_receipt_validates_and_reports_on_hand(client, application):
    _all_staff(application)
    _customer(client, application)
    warehouse = _warehouse(client)
    _receipt_validate(client, warehouse, "PANEL-550", "100.0000")
    levels = client.get("/api/v1/stock", headers=warehouse)
    assert levels.status_code == 200, levels.text
    panel = [row for row in levels.json() if row["component_code"] == "PANEL-550"]
    assert panel and float(panel[0]["on_hand"]) == 100.0


def test_draft_operation_cannot_validate_and_double_validate_fails(client, application):
    _all_staff(application)
    _customer(client, application)
    warehouse = _warehouse(client)
    created = client.post(
        "/api/v1/stock/operations",
        json={
            "operation_type": "receipt",
            "lines": [{"component_code": "PANEL-550", "quantity": "10", "to_location": "MAIN"}],
        },
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    operation_id = created.json()["id"]
    direct = client.post(f"/api/v1/stock/operations/{operation_id}/validate", headers=warehouse)
    assert direct.status_code == 409, direct.text
    assert direct.json()["error"]["code"] == "invalid_transition"
    assert (
        client.post(f"/api/v1/stock/operations/{operation_id}/ready", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/stock/operations/{operation_id}/validate", headers=warehouse
        ).status_code
        == 200
    )
    again = client.post(f"/api/v1/stock/operations/{operation_id}/validate", headers=warehouse)
    assert again.status_code == 409, again.text


def test_failed_transfer_and_delivery_leave_ledger_unchanged(client, application):
    _all_staff(application)
    _customer(client, application)
    warehouse = _warehouse(client)
    _receipt_validate(client, warehouse, "PANEL-550", "20.0000", "MAIN")
    with Session(application.state.engine) as db:
        before = db.scalar(select(func.count()).select_from(StockLedger))

    def _draft_validate(operation_type: str, line: dict) -> dict:
        created = client.post(
            "/api/v1/stock/operations",
            json={"operation_type": operation_type, "lines": [line]},
            headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
        )
        assert created.status_code == 201, created.text
        operation_id = created.json()["id"]
        assert (
            client.post(
                f"/api/v1/stock/operations/{operation_id}/ready", headers=warehouse
            ).status_code
            == 200
        )
        failed = client.post(f"/api/v1/stock/operations/{operation_id}/validate", headers=warehouse)
        assert failed.status_code == 409, failed.text
        assert failed.json()["error"]["code"] == "insufficient_stock"
        return failed.json()

    _draft_validate(
        "transfer",
        {
            "component_code": "PANEL-550",
            "quantity": "999",
            "from_location": "MAIN",
            "to_location": "SITE",
        },
    )
    _draft_validate(
        "delivery", {"component_code": "PANEL-550", "quantity": "999", "from_location": "MAIN"}
    )
    _draft_validate(
        "adjustment",
        {"component_code": "PANEL-550", "quantity": "-999", "to_location": "MAIN"},
    )
    with Session(application.state.engine) as db:
        after = db.scalar(select(func.count()).select_from(StockLedger))
    assert after == before
    levels = client.get("/api/v1/stock", headers=warehouse)
    panel = [row for row in levels.json() if row["component_code"] == "PANEL-550"]
    assert float(panel[0]["on_hand"]) == 20.0


def test_concurrent_validation_has_a_single_winner(client, application):
    _all_staff(application)
    _customer(client, application)
    warehouse = _warehouse(client)
    _receipt_validate(client, warehouse, "PANEL-550", "50.0000", "MAIN")
    created = client.post(
        "/api/v1/stock/operations",
        json={
            "operation_type": "delivery",
            "lines": [{"component_code": "PANEL-550", "quantity": "5", "from_location": "MAIN"}],
        },
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    operation_id = created.json()["id"]
    assert (
        client.post(f"/api/v1/stock/operations/{operation_id}/ready", headers=warehouse).status_code
        == 200
    )
    with Session(application.state.engine) as db:
        actor = db.scalar(select(User).where(User.email == "wh@example.com"))
        assert actor is not None
        actor_id = actor.id
    barrier = threading.Barrier(2)
    results: list[str] = []

    def _race() -> None:
        session = application.state.session_factory()
        try:
            user = session.get(User, actor_id)
            assert user is not None
            barrier.wait()
            validate_operation(session, user, uuid.UUID(operation_id))
            session.commit()
            results.append("ok")
        except AppError as exc:
            session.rollback()
            results.append(exc.code)
        finally:
            session.close()

    threads = [threading.Thread(target=_race), threading.Thread(target=_race)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["invalid_transition", "ok"]
    with Session(application.state.engine) as db:
        deltas = db.scalars(
            select(StockLedger.quantity_delta).where(
                StockLedger.operation_id == uuid.UUID(operation_id)
            )
        ).all()
    assert sum(float(item) for item in deltas) == -5.0


def test_confirmed_order_creates_reservations(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    sales = _sales(client)
    reserved = client.get(f"/api/v1/stock/reservations?order_id={order['id']}", headers=sales)
    assert reserved.status_code == 200, reserved.text
    assert reserved.json(), "Order confirmation must create material reservations."
    assert {row["status"] for row in reserved.json()} == {"reserved"}


def test_serial_scan_is_unique_and_rejects_done_operations(client, application):
    _all_staff(application)
    _customer(client, application)
    warehouse = _warehouse(client)
    first = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": "SN-PANEL-0001", "component_code": "PANEL-550"},
        headers=warehouse,
    )
    assert first.status_code == 201, first.text
    duplicate = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": "sn-panel-0001", "component_code": "PANEL-550"},
        headers=warehouse,
    )
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["error"]["code"] == "serial_exists"
    validated = _receipt_validate(client, warehouse, "PANEL-550", "1.0000")
    locked = client.post(
        "/api/v1/serials/scan",
        json={
            "serial_number": "SN-PANEL-0002",
            "component_code": "PANEL-550",
            "operation_id": validated["id"],
        },
        headers=warehouse,
    )
    assert locked.status_code == 409, locked.text


def test_replenishment_staff_cannot_approve(client, application):
    _all_staff(application)
    _customer(client, application)
    warehouse = _warehouse(client)
    proposed = client.post(
        "/api/v1/replenishment/requests",
        json={"component_code": "PANEL-550", "location_code": "MAIN", "quantity": 40},
        headers=warehouse,
    )
    assert proposed.status_code == 201, proposed.text
    request_id = proposed.json()["id"]
    staff_decision = client.post(
        f"/api/v1/replenishment/requests/{request_id}/decision",
        json={"decision": "approve"},
        headers=warehouse,
    )
    assert staff_decision.status_code == 403, staff_decision.text
    manager = _manager(client)
    approved = client.post(
        f"/api/v1/replenishment/requests/{request_id}/decision",
        json={"decision": "approve"},
        headers=manager,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["decided_by_user_id"]
    repeat = client.post(
        f"/api/v1/replenishment/requests/{request_id}/decision",
        json={"decision": "reject"},
        headers=manager,
    )
    assert repeat.status_code == 409, repeat.text


def test_delivery_confirm_activates_warranty_and_blocks_replay(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    warehouse = _warehouse(client)
    with Session(application.state.engine) as db:
        job_order = db.get(SalesOrder, uuid.UUID(order["id"]))
        assert job_order is not None
        material = [
            (line.component_code, line.quantity)
            for line in job_order.lines
            if line.line_kind == "material"
        ]
    for component_code, quantity in material:
        assert component_code is not None
        _receipt_validate(client, warehouse, component_code, f"{quantity}.0000", "MAIN")
    created = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    delivery_id = created.json()["id"]
    assert created.json()["lines"], "Delivery must carry the picked material lines."
    replay = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert replay.status_code == 409, replay.text
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/transit", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/deliver", headers=warehouse).status_code
        == 200
    )
    technician = _technician(client)
    confirmed = client.post(f"/api/v1/deliveries/{delivery_id}/confirm", headers=technician)
    assert confirmed.status_code == 200, confirmed.text
    sales = _sales(client)
    warranty = client.get(f"/api/v1/warranties/order/{order['id']}", headers=sales)
    assert warranty.status_code == 200, warranty.text
    assert warranty.json()["status"] == "active"
    starts = datetime.fromisoformat(warranty.json()["starts_at"])
    ends = datetime.fromisoformat(warranty.json()["ends_at"])
    assert (ends - starts).days >= 365 * 4
    support = _support(client)
    voided = client.post(f"/api/v1/warranties/order/{order['id']}/void", headers=support)
    assert voided.status_code == 200, voided.text
    assert voided.json()["status"] == "void"
    consumed = client.get(
        f"/api/v1/stock/reservations?order_id={order['id']}", headers=_sales(client)
    )
    assert {row["status"] for row in consumed.json()} == {"consumed"}


def test_picking_without_stock_fails(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="nostock@example.com")
    warehouse = _warehouse(client)
    created = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 409, created.text
    assert created.json()["error"]["code"] == "insufficient_stock"


def test_job_completion_requires_otp_evidence_and_signature(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    sales = _sales(client)
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        assert tech is not None
        tech_id = str(tech.id)
    created = client.post(
        "/api/v1/jobs",
        json={"order_id": order["id"], "technician_user_id": tech_id},
        headers=sales,
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    customer_code = created.json()["customer_code"]
    assert customer_code and len(customer_code) == 6
    technician = _technician(client)
    early = client.post(f"/api/v1/jobs/{job_id}/completion", headers=technician)
    assert early.status_code == 409, early.text
    assert early.json()["error"]["code"] == "otp_required"
    wrong = client.post(
        f"/api/v1/jobs/{job_id}/customer-otp", json={"code": "000000"}, headers=technician
    )
    assert wrong.status_code == 400, wrong.text
    assert client.post(f"/api/v1/jobs/{job_id}/arrival", headers=technician).status_code == 200
    verified = client.post(
        f"/api/v1/jobs/{job_id}/customer-otp", json={"code": customer_code}, headers=technician
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["otp_verified"] is True
    now = datetime.now(UTC).isoformat()
    evidence = client.post(
        f"/api/v1/jobs/{job_id}/evidence",
        json={
            "photo_refs": ["JOB-PHOTO-1"],
            "test_readings": {"voc_v": 612.5},
            "started_at": now,
            "finished_at": now,
        },
        headers=technician,
    )
    assert evidence.status_code == 200, evidence.text
    no_confirm = client.post(
        f"/api/v1/jobs/{job_id}/signature",
        json={"signature_ref": "SIG-1", "customer_confirmed": False},
        headers=technician,
    )
    assert no_confirm.status_code == 400, no_confirm.text
    signed = client.post(
        f"/api/v1/jobs/{job_id}/signature",
        json={"signature_ref": "SIG-1", "customer_confirmed": True},
        headers=technician,
    )
    assert signed.status_code == 200, signed.text
    done = client.post(f"/api/v1/jobs/{job_id}/completion", headers=technician)
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"
    assert done.json()["arrival_at"]


def test_customer_cannot_touch_warehouse_and_scheduling_guards(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="phase3cust@example.com")
    customer = _login(client, "customer", "phase3cust@example.com", "Solarops123")
    denied = client.post(
        "/api/v1/stock/operations",
        json={
            "operation_type": "receipt",
            "lines": [{"component_code": "PANEL-550", "quantity": "1", "to_location": "MAIN"}],
        },
        headers={**customer, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert denied.status_code == 403, denied.text
    assert client.get("/api/v1/stock", headers=customer).status_code == 403
    assert (
        client.get(
            f"/api/v1/stock/reservations?order_id={order['id']}", headers=customer
        ).status_code
        == 403
    )
    sales = _sales(client)
    scheduling = client.get("/api/v1/scheduling/installations", headers=sales)
    assert scheduling.status_code == 200, scheduling.text
    scheduling_id = [row for row in scheduling.json() if row["order_id"] == order["id"]][0]["id"]
    slot = datetime.now(UTC).isoformat()
    scheduled = client.post(
        f"/api/v1/scheduling/installations/{scheduling_id}/slot",
        json={"slot_starts_at": slot},
        headers=sales,
    )
    assert scheduled.status_code == 200, scheduled.text
    assert scheduled.json()["status"] == "scheduled"
    recommendations = client.post(
        "/api/v1/assignments/recommendations",
        json={"order_id": order["id"]},
        headers=sales,
    )
    assert recommendations.status_code == 200, recommendations.text
    assert recommendations.json(), "At least one technician must be recommended."
    assert client.get("/api/v1/jobs", headers=customer).status_code == 200


def test_cross_phase_order_to_completed_installation(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="endtoend@example.com")
    warehouse = _warehouse(client)
    with Session(application.state.engine) as db:
        job_order = db.get(SalesOrder, uuid.UUID(order["id"]))
        assert job_order is not None
        material = [
            (line.component_code, line.quantity)
            for line in job_order.lines
            if line.line_kind == "material"
        ]
    assert material
    for component_code, quantity in material:
        assert component_code is not None
        _receipt_validate(client, warehouse, component_code, f"{quantity}.0000", "MAIN")
    delivery = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert delivery.status_code == 201, delivery.text
    delivery_id = delivery.json()["id"]
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/transit", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/deliver", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/confirm", headers=warehouse).status_code
        == 200
    )
    sales = _sales(client)
    warranty = client.get(f"/api/v1/warranties/order/{order['id']}", headers=sales)
    assert warranty.json()["status"] == "active"
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        assert tech is not None
        tech_id = str(tech.id)
    job = client.post(
        "/api/v1/jobs",
        json={"order_id": order["id"], "technician_user_id": tech_id},
        headers=sales,
    )
    assert job.status_code == 201, job.text
    job_id, customer_code = job.json()["id"], job.json()["customer_code"]
    technician = _technician(client)
    assert client.post(f"/api/v1/jobs/{job_id}/arrival", headers=technician).status_code == 200
    assert (
        client.post(
            f"/api/v1/jobs/{job_id}/customer-otp", json={"code": customer_code}, headers=technician
        ).status_code
        == 200
    )
    now = datetime.now(UTC).isoformat()
    assert (
        client.post(
            f"/api/v1/jobs/{job_id}/evidence",
            json={
                "photo_refs": ["E2E-1"],
                "test_readings": {},
                "started_at": now,
                "finished_at": now,
            },
            headers=technician,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/jobs/{job_id}/signature",
            json={"signature_ref": "E2E-SIG", "customer_confirmed": True},
            headers=technician,
        ).status_code
        == 200
    )
    done = client.post(f"/api/v1/jobs/{job_id}/completion", headers=technician)
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(InstallationJob)) == 1


def _order_material(application, order_id: str) -> list[tuple[str, int]]:
    with Session(application.state.engine) as db:
        order = db.get(SalesOrder, uuid.UUID(order_id))
        assert order is not None
        return [
            (line.component_code, line.quantity)
            for line in order.lines
            if line.line_kind == "material" and line.component_code is not None
        ]


def _receipt_material(
    client, warehouse: dict, material: list[tuple[str, int]], location: str = "MAIN"
) -> None:
    for component_code, quantity in material:
        _receipt_validate(client, warehouse, component_code, f"{quantity}.0000", location)


def test_competing_orders_cannot_pick_the_same_stock(client, application):
    _all_staff(application)
    order_a = _confirmed_order(client, application, email="compete-a@example.com")
    order_b = _confirmed_order(client, application, email="compete-b@example.com")
    warehouse = _warehouse(client)
    material = _order_material(application, order_a["id"])
    assert material
    _receipt_material(client, warehouse, material)
    first = client.post(
        "/api/v1/deliveries",
        json={"order_id": order_a["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert first.status_code == 201, first.text
    with Session(application.state.engine) as db:
        panel = material[0][0]
        remaining = db.scalar(
            select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
                StockLedger.component_code == panel, StockLedger.location_code == "MAIN"
            )
        )
    assert int(remaining or 0) == 0
    second = client.post(
        "/api/v1/deliveries",
        json={"order_id": order_b["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert second.status_code == 409, second.text
    assert second.json()["error"]["code"] == "insufficient_stock"
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Delivery)) == 1
        reserved_b = db.scalars(select(StockLedger.id).where(StockLedger.quantity_delta < 0)).all()
        assert len(reserved_b) == len(material)
        kept = db.scalar(
            select(StockReservation.status).where(
                StockReservation.order_id == uuid.UUID(order_b["id"])
            )
        )
        assert kept == "reserved"
    assert (
        client.post(
            f"/api/v1/deliveries/{first.json()['id']}/transit", headers=warehouse
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/deliveries/{first.json()['id']}/deliver", headers=warehouse
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/deliveries/{first.json()['id']}/confirm", headers=warehouse
        ).status_code
        == 200
    )


def test_duplicate_delivery_confirmation_fails(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="dupconfirm@example.com")
    warehouse = _warehouse(client)
    _receipt_material(client, warehouse, _order_material(application, order["id"]))
    created = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    delivery_id = created.json()["id"]
    early = client.post(f"/api/v1/deliveries/{delivery_id}/confirm", headers=warehouse)
    assert early.status_code == 409, early.text
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/transit", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/deliver", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/confirm", headers=warehouse).status_code
        == 200
    )
    repeat = client.post(f"/api/v1/deliveries/{delivery_id}/confirm", headers=warehouse)
    assert repeat.status_code == 409, repeat.text
    assert repeat.json()["error"]["code"] == "invalid_transition"


def test_site_stock_must_transfer_to_main_before_pick(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="location@example.com")
    warehouse = _warehouse(client)
    material = _order_material(application, order["id"])
    _receipt_material(client, warehouse, material, location="SITE")
    blocked = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["code"] == "insufficient_stock"
    moved = client.post(
        "/api/v1/stock/operations",
        json={
            "operation_type": "transfer",
            "lines": [
                {
                    "component_code": code,
                    "quantity": str(quantity),
                    "from_location": "SITE",
                    "to_location": "MAIN",
                }
                for code, quantity in material
            ],
        },
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert moved.status_code == 201, moved.text
    operation_id = moved.json()["id"]
    assert (
        client.post(f"/api/v1/stock/operations/{operation_id}/ready", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/stock/operations/{operation_id}/validate", headers=warehouse
        ).status_code
        == 200
    )
    picked = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert picked.status_code == 201, picked.text
    levels = client.get("/api/v1/stock", headers=warehouse).json()
    main_panel = [
        row
        for row in levels
        if row["component_code"] == material[0][0] and row["location_code"] == "MAIN"
    ]
    assert main_panel and float(main_panel[0]["on_hand"]) == 0.0


def test_serial_assign_install_and_mismatch(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="serial@example.com")
    warehouse = _warehouse(client)
    material = _order_material(application, order["id"])
    component = material[0][0]
    scanned = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": "SN-ASSIGN-001", "component_code": component},
        headers=warehouse,
    )
    assert scanned.status_code == 201, scanned.text
    serial_id = scanned.json()["id"]
    with Session(application.state.engine) as db:
        from app.models.workflow import CatalogueComponent

        other = db.scalar(
            select(CatalogueComponent.code).where(
                ~CatalogueComponent.code.in_([code for code, _ in material])
            )
        )
    assert other is not None
    wrong_scan = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": "SN-ASSIGN-002", "component_code": other},
        headers=warehouse,
    )
    assert wrong_scan.status_code == 201, wrong_scan.text
    mismatch = client.post(
        f"/api/v1/serials/{wrong_scan.json()['id']}/assign",
        json={"order_id": order["id"]},
        headers=warehouse,
    )
    assert mismatch.status_code == 409, mismatch.text
    assert mismatch.json()["error"]["code"] == "serial_component_mismatch"
    assigned = client.post(
        f"/api/v1/serials/{serial_id}/assign",
        json={"order_id": order["id"]},
        headers=warehouse,
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "reserved"
    assert assigned.json()["order_id"] == order["id"]
    repeat_assign = client.post(
        f"/api/v1/serials/{serial_id}/assign",
        json={"order_id": order["id"]},
        headers=warehouse,
    )
    assert repeat_assign.status_code == 409, repeat_assign.text
    _receipt_material(client, warehouse, material)
    created = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    delivery_id = created.json()["id"]
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/transit", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/deliver", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/confirm", headers=warehouse).status_code
        == 200
    )
    with Session(application.state.engine) as db:
        status = db.scalar(
            select(EquipmentSerial.status).where(EquipmentSerial.id == uuid.UUID(serial_id))
        )
    assert status == "installed"


def test_foreign_technician_cannot_touch_assigned_job(client, application):
    _all_staff(application)
    _staff(application, "technician", "tech2@example.com", "EMP-TECH-902")
    order = _confirmed_order(client, application, email="foreigntech@example.com")
    sales = _sales(client)
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        assert tech is not None
        tech_id = str(tech.id)
    created = client.post(
        "/api/v1/jobs",
        json={"order_id": order["id"], "technician_user_id": tech_id},
        headers=sales,
    )
    job_id = created.json()["id"]
    intruder = _login(client, "employee", "EMP-TECH-902", "Staffpass123")
    assert client.post(f"/api/v1/jobs/{job_id}/arrival", headers=intruder).status_code == 404
    assert (
        client.post(
            f"/api/v1/jobs/{job_id}/customer-otp", json={"code": "123456"}, headers=intruder
        ).status_code
        == 404
    )
    assert client.post(f"/api/v1/jobs/{job_id}/completion", headers=intruder).status_code == 404
    assert client.get(f"/api/v1/jobs/{job_id}", headers=intruder).status_code == 404
    assert client.get("/api/v1/jobs", headers=intruder).json() == []


def test_expired_and_reused_customer_otp_fail(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="otp@example.com")
    sales = _sales(client)
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        assert tech is not None
        tech_id = str(tech.id)
    created = client.post(
        "/api/v1/jobs",
        json={"order_id": order["id"], "technician_user_id": tech_id},
        headers=sales,
    )
    job_id, customer_code = created.json()["id"], created.json()["customer_code"]
    technician = _technician(client)
    with Session(application.state.engine) as db:
        challenge = db.scalar(
            select(InstallationOtp).where(InstallationOtp.job_id == uuid.UUID(job_id))
        )
        assert challenge is not None
        challenge.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    expired = client.post(
        f"/api/v1/jobs/{job_id}/customer-otp", json={"code": customer_code}, headers=technician
    )
    assert expired.status_code == 409, expired.text
    assert expired.json()["error"]["code"] == "otp_expired"
    with Session(application.state.engine) as db:
        challenge = db.scalar(
            select(InstallationOtp).where(InstallationOtp.job_id == uuid.UUID(job_id))
        )
        assert challenge is not None
        challenge.expires_at = utcnow() + timedelta(minutes=30)
        db.commit()
    verified = client.post(
        f"/api/v1/jobs/{job_id}/customer-otp", json={"code": customer_code}, headers=technician
    )
    assert verified.status_code == 200, verified.text
    reused = client.post(
        f"/api/v1/jobs/{job_id}/customer-otp", json={"code": customer_code}, headers=technician
    )
    assert reused.status_code == 409, reused.text
    assert reused.json()["error"]["code"] == "otp_missing"


def test_warranty_void_guards_and_failed_pick_creates_nothing(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="void@example.com")
    warehouse = _warehouse(client)
    with Session(application.state.engine) as db:
        deliveries_before = db.scalar(select(func.count()).select_from(Delivery))
        ledger_before = db.scalar(select(func.count()).select_from(StockLedger))
    failed = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert failed.status_code == 409, failed.text
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(Delivery)) == deliveries_before
        assert db.scalar(select(func.count()).select_from(StockLedger)) == ledger_before
    _receipt_material(client, warehouse, _order_material(application, order["id"]))
    created = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    delivery_id = created.json()["id"]
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/transit", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/deliver", headers=warehouse).status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/deliveries/{delivery_id}/confirm", headers=warehouse).status_code
        == 200
    )
    staff_void = client.post(f"/api/v1/warranties/order/{order['id']}/void", headers=warehouse)
    assert staff_void.status_code == 403, staff_void.text
    support = _support(client)
    assert (
        client.post(f"/api/v1/warranties/order/{order['id']}/void", headers=support).status_code
        == 200
    )
    second_void = client.post(f"/api/v1/warranties/order/{order['id']}/void", headers=support)
    assert second_void.status_code == 409, second_void.text


def test_delivery_cancel_restocks_main(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application, email="cancel@example.com")
    warehouse = _warehouse(client)
    material = _order_material(application, order["id"])
    _receipt_material(client, warehouse, material)
    created = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    delivery_id = created.json()["id"]
    levels = client.get("/api/v1/stock", headers=warehouse).json()
    picked = [
        row
        for row in levels
        if row["component_code"] == material[0][0] and row["location_code"] == "MAIN"
    ]
    assert float(picked[0]["on_hand"]) == 0.0
    cancelled = client.post(f"/api/v1/deliveries/{delivery_id}/cancel", headers=warehouse)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    restored = client.get("/api/v1/stock", headers=warehouse).json()
    back = [
        row
        for row in restored
        if row["component_code"] == material[0][0] and row["location_code"] == "MAIN"
    ]
    assert float(back[0]["on_hand"]) == float(material[0][1])
    late = client.post(f"/api/v1/deliveries/{delivery_id}/transit", headers=warehouse)
    assert late.status_code == 409, late.text


def test_concurrent_picks_serialize_on_component_locks(client, application):
    _all_staff(application)
    _customer(client, application)
    warehouse = _warehouse(client)
    _receipt_validate(client, warehouse, "PANEL-550", "10.0000", "MAIN")
    operation_ids: list[str] = []
    for _ in range(2):
        created = client.post(
            "/api/v1/stock/operations",
            json={
                "operation_type": "delivery",
                "lines": [
                    {"component_code": "PANEL-550", "quantity": "10", "from_location": "MAIN"}
                ],
            },
            headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
        )
        assert created.status_code == 201, created.text
        operation_ids.append(created.json()["id"])
        assert (
            client.post(
                f"/api/v1/stock/operations/{created.json()['id']}/ready", headers=warehouse
            ).status_code
            == 200
        )
    with Session(application.state.engine) as db:
        actor = db.scalar(select(User).where(User.email == "wh@example.com"))
        assert actor is not None
        actor_id = actor.id
    barrier = threading.Barrier(2)
    results: list[str] = []

    def _race(operation_id: str) -> None:
        session = application.state.session_factory()
        try:
            user = session.get(User, actor_id)
            assert user is not None
            barrier.wait()
            validate_operation(session, user, uuid.UUID(operation_id))
            session.commit()
            results.append("ok")
        except AppError as exc:
            session.rollback()
            results.append(exc.code)
        finally:
            session.close()

    threads = [
        threading.Thread(target=_race, args=(operation_id,)) for operation_id in operation_ids
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["insufficient_stock", "ok"]
    with Session(application.state.engine) as db:
        total = db.scalar(
            select(func.coalesce(func.sum(StockLedger.quantity_delta), 0)).where(
                StockLedger.component_code == "PANEL-550", StockLedger.location_code == "MAIN"
            )
        )
    assert int(total or 0) == 0
