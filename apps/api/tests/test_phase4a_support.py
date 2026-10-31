"""Phase 4A support workflow: complaint to customer-confirmed resolution.

Every test runs against PostgreSQL through the real API, reusing the genuine
Phase 3 pipeline (order, stock receipt, serial assignment, delivery confirm,
warranty activation) so tickets always reference real installed equipment.
"""

import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.errors import AppError
from app.core.security import hash_password, utcnow
from app.models.identity import EmployeeProfile, User
from app.models.support import ResolutionAcknowledgment, ServiceTicket
from app.models.workflow import SalesOrder
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


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
    _staff(application, "technician", "tech2@example.com", "EMP-TECH-902")
    _staff(application, "warehouse_staff", "wh@example.com", "EMP-WH-901")
    _staff(application, "support", "support@example.com", "EMP-SUP-901")


def _warehouse(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-WH-901", "Staffpass123")


def _sales(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-SALES-901", "Staffpass123")


def _technician(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-TECH-901", "Staffpass123")


def _technician2(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-TECH-902", "Staffpass123")


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
    assert (
        client.patch(
            f"/api/v1/enquiries/{enquiry_id}/qualification",
            json={"status": "under_review", "note": "Checking the roof."},
            headers=sales,
        ).status_code
        == 200
    )
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
    assert (
        client.post(
            f"/api/v1/surveys/{survey_id}/assignment",
            json={"technician_user_id": tech_id},
            headers=sales,
        ).status_code
        == 200
    )
    technician = _technician(client)
    assert client.post(f"/api/v1/surveys/{survey_id}/start", headers=technician).status_code == 200
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


def _receipt_validate(client, headers, component: str, quantity: str, location: str = "MAIN"):
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
    assert client.post(f"/api/v1/stock/operations/{operation_id}/ready", headers=headers).status_code == 200
    validated = client.post(f"/api/v1/stock/operations/{operation_id}/validate", headers=headers)
    assert validated.status_code == 200, validated.text
    return validated.json()


def _order_material(application, order_id: str) -> list[tuple[str, int]]:
    with Session(application.state.engine) as db:
        order = db.get(SalesOrder, uuid.UUID(order_id))
        assert order is not None
        return [
            (line.component_code, line.quantity)
            for line in order.lines
            if line.line_kind == "material" and line.component_code is not None
        ]


def _installed_order(client, application, email: str = "leela@example.com",
                     serial: str = "SN-INV-0001") -> tuple[dict, str]:
    """Confirmed order with one installed serial and an active warranty."""
    order = _confirmed_order(client, application, email)
    warehouse = _warehouse(client)
    for component_code, quantity in _order_material(application, order["id"]):
        _receipt_validate(client, warehouse, component_code, f"{quantity}.0000", "MAIN")
    scanned = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": serial, "component_code": _order_material(application, order["id"])[0][0]},
        headers=warehouse,
    )
    assert scanned.status_code == 201, scanned.text
    assigned = client.post(
        f"/api/v1/serials/{scanned.json()['id']}/assign",
        json={"order_id": order["id"]},
        headers=warehouse,
    )
    assert assigned.status_code == 200, assigned.text
    created = client.post(
        "/api/v1/deliveries",
        json={"order_id": order["id"]},
        headers={**warehouse, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    delivery_id = created.json()["id"]
    assert client.post(f"/api/v1/deliveries/{delivery_id}/transit", headers=warehouse).status_code == 200
    assert client.post(f"/api/v1/deliveries/{delivery_id}/deliver", headers=warehouse).status_code == 200
    assert client.post(f"/api/v1/deliveries/{delivery_id}/confirm", headers=warehouse).status_code == 200
    warranty = client.get(f"/api/v1/warranties/order/{order['id']}", headers=_sales(client))
    assert warranty.json()["status"] == "active", warranty.text
    return order, serial


def _ticket_payload(order_id: str, serial: str | None = "SN-INV-0001") -> dict:
    payload = {
        "order_id": order_id,
        "fault_code": "E-07",
        "symptoms": "The inverter shows fault code E-07 every afternoon and stops feeding power.",
        "customer_urgency": "high",
        "contact_preference": "phone",
    }
    if serial is not None:
        payload["serial_number"] = serial
    return payload


def _create_ticket(client, customer: dict[str, str], order_id: str,
                   serial: str | None = "SN-INV-0001") -> dict:
    created = client.post(
        "/api/v1/tickets",
        json=_ticket_payload(order_id, serial),
        headers={**customer, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    return created.json()


def _tech_id(application, email: str) -> str:
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == email))
        assert tech is not None
        return str(tech.id)


def _triage(client, ticket_id: str) -> dict:
    response = client.post(
        f"/api/v1/tickets/{ticket_id}/triage",
        json={"category": "inverter", "verified_priority": "high",
              "note": "Fault code points at the inverter; treating as high severity."},
        headers=_support(client),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _repair_job(client, ticket_id: str, technician_id: str) -> dict:
    response = client.post(
        f"/api/v1/tickets/{ticket_id}/repair-jobs",
        json={"technician_user_id": technician_id, "note": "Inverter specialist required."},
        headers={**_support(client), "Idempotency-Key": uuid.uuid4().hex},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _record_full_repair(client, job_id: str, technician: dict[str, str]) -> None:
    assert client.post(f"/api/v1/repair-jobs/{job_id}/arrival", headers=technician).status_code == 200
    diagnostics = client.post(
        f"/api/v1/repair-jobs/{job_id}/diagnostics",
        json={"findings": "DC isolator contacts pitted; inverter itself healthy.",
              "root_cause": "Worn isolator", "readings": {"voc_v": 612.5}},
        headers=technician,
    )
    assert diagnostics.status_code == 200, diagnostics.text
    now = datetime.now(UTC)
    work = client.post(
        f"/api/v1/repair-jobs/{job_id}/work",
        json={
            "work_performed": "Replaced the DC isolator, retorqued terminals, verified generation.",
            "work_started_at": (now - timedelta(hours=2)).isoformat(),
            "work_finished_at": now.isoformat(),
            "parts_used": [{"component_code": "PANEL-550", "quantity": 1}],
        },
        headers=technician,
    )
    assert work.status_code == 200, work.text
    submit = client.post(
        f"/api/v1/repair-jobs/{job_id}/submit",
        json={"summary": "Isolator replaced and generation verified at 2.9 kW under load."},
        headers=technician,
    )
    assert submit.status_code == 200, submit.text


def test_customer_creates_ticket_with_installed_serial(client, application):
    _all_staff(application)
    order, serial = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"], serial)
    assert ticket["status"] == "open"
    assert ticket["reference"].startswith("TKT-")
    assert ticket["serial_number"] == serial.upper()
    assert ticket["customer_urgency"] == "high"
    assert ticket["verified_priority"] is None
    assert ticket["warranty"] and ticket["warranty"]["status"] == "active"
    history = client.get(f"/api/v1/tickets/{ticket['id']}/history", headers=customer)
    assert history.status_code == 200, history.text
    assert [event["action"] for event in history.json()] == ["created"]


def test_ticket_create_rejects_other_customer_order(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    other = _customer(client, application, "neighbour@example.com")
    denied = client.post(
        "/api/v1/tickets",
        json=_ticket_payload(order["id"]),
        headers={**other, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert denied.status_code == 404, denied.text
    assert denied.json()["error"]["code"] == "not_found"


def test_ticket_create_rejects_uninstalled_serial(client, application):
    _all_staff(application)
    order = _confirmed_order(client, application)
    warehouse = _warehouse(client)
    component = _order_material(application, order["id"])[0][0]
    scanned = client.post(
        "/api/v1/serials/scan",
        json={"serial_number": "SN-RESERVED-1", "component_code": component},
        headers=warehouse,
    )
    assert scanned.status_code == 201, scanned.text
    assert (
        client.post(
            f"/api/v1/serials/{scanned.json()['id']}/assign",
            json={"order_id": order["id"]},
            headers=warehouse,
        ).status_code
        == 200
    )
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    rejected = client.post(
        "/api/v1/tickets",
        json=_ticket_payload(order["id"], "SN-RESERVED-1"),
        headers={**customer, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"]["code"] == "serial_not_installed"
    unknown = client.post(
        "/api/v1/tickets",
        json=_ticket_payload(order["id"], "SN-NOPE-9999"),
        headers={**customer, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert unknown.status_code == 404, unknown.text


def test_ticket_create_is_idempotent(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    key = uuid.uuid4().hex
    first = client.post(
        "/api/v1/tickets", json=_ticket_payload(order["id"]),
        headers={**customer, "Idempotency-Key": key},
    )
    assert first.status_code == 201, first.text
    replay = client.post(
        "/api/v1/tickets", json=_ticket_payload(order["id"]),
        headers={**customer, "Idempotency-Key": key},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == first.json()["id"]
    conflict = client.post(
        "/api/v1/tickets", json=_ticket_payload(order["id"], None),
        headers={**customer, "Idempotency-Key": key},
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "idempotency_conflict"


def test_support_triage_sets_verified_priority(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"])
    triaged = _triage(client, ticket["id"])
    assert triaged["status"] == "triaged"
    assert triaged["category"] == "inverter"
    assert triaged["verified_priority"] == "high"
    assert triaged["customer_urgency"] == "high"


def test_invalid_transitions_rejected(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"])
    support = _support(client)
    early_close = client.post(
        f"/api/v1/tickets/{ticket['id']}/close",
        json={"reason": "Trying to skip the workflow."},
        headers=support,
    )
    assert early_close.status_code == 409, early_close.text
    early_ready = client.post(
        f"/api/v1/tickets/{ticket['id']}/resolution-ready",
        json={"summary": "No work has been recorded yet."},
        headers=support,
    )
    assert early_ready.status_code == 409, early_ready.text
    assert early_ready.json()["error"]["code"] == "invalid_transition"
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    customer_close = client.post(
        f"/api/v1/tickets/{ticket['id']}/close",
        json={"reason": "Customer trying to close."},
        headers=customer,
    )
    assert customer_close.status_code == 403, customer_close.text


def test_repair_assignment_and_technician_isolation(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"])
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    assert job["status"] == "assigned"
    assert job["reference"].startswith("RPJ-")
    detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=_support(client))
    assert detail.json()["status"] == "assigned"
    technician = _technician(client)
    mine = client.get("/api/v1/repair-jobs", headers=technician)
    assert mine.status_code == 200, mine.text
    assert {row["id"] for row in mine.json()} == {job["id"]}
    other = _technician2(client)
    assert client.get("/api/v1/repair-jobs", headers=other).json() == []
    stranger = client.get(f"/api/v1/repair-jobs/{job['id']}", headers=other)
    assert stranger.status_code == 404, stranger.text
    technician = _technician(client)
    seen = client.get(f"/api/v1/repair-jobs/{job['id']}", headers=technician)
    assert seen.status_code == 200, seen.text


def test_technician_availability_is_enforced(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    slot = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0).isoformat()
    first = _create_ticket(client, customer, order["id"])
    _triage(client, first["id"])
    support = _support(client)
    response = client.post(
        f"/api/v1/tickets/{first['id']}/repair-jobs",
        json={"technician_user_id": _tech_id(application, "tech@example.com"),
              "scheduled_starts_at": slot},
        headers={**support, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert response.status_code == 201, response.text
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    second = _create_ticket(client, customer, order["id"])
    _triage(client, second["id"])
    support = _support(client)
    clash = client.post(
        f"/api/v1/tickets/{second['id']}/repair-jobs",
        json={"technician_user_id": _tech_id(application, "tech@example.com"),
              "scheduled_starts_at": slot},
        headers={**support, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert clash.status_code == 409, clash.text
    assert clash.json()["error"]["code"] == "technician_unavailable"


def test_repair_submit_requires_recorded_work(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"])
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    technician = _technician(client)
    early = client.post(
        f"/api/v1/repair-jobs/{job['id']}/submit",
        json={"summary": "Trying to submit without any recorded site work at all."},
        headers=technician,
    )
    assert early.status_code == 409, early.text
    assert early.json()["error"]["code"] == "arrival_required"
    assert client.post(f"/api/v1/repair-jobs/{job['id']}/arrival", headers=technician).status_code == 200
    no_diag = client.post(
        f"/api/v1/repair-jobs/{job['id']}/submit",
        json={"summary": "Trying to submit diagnostics-free repair work summary here."},
        headers=technician,
    )
    assert no_diag.json()["error"]["code"] == "diagnostics_required"
    bad_times = client.post(
        f"/api/v1/repair-jobs/{job['id']}/work",
        json={
            "work_performed": "Work that finishes before it starts is impossible.",
            "work_started_at": datetime.now(UTC).isoformat(),
            "work_finished_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "parts_used": [],
        },
        headers=technician,
    )
    assert bad_times.status_code == 422, bad_times.text
    unknown_part = client.post(
        f"/api/v1/repair-jobs/{job['id']}/work",
        json={
            "work_performed": "Installed a part that the catalogue has never heard of.",
            "work_started_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "work_finished_at": datetime.now(UTC).isoformat(),
            "parts_used": [{"component_code": "NOPE-1", "quantity": 1}],
        },
        headers=technician,
    )
    assert unknown_part.status_code == 404, unknown_part.text


def _upload(client, ticket_id: str, headers: dict, filename: str = "fault.png",
            payload: bytes = PNG_BYTES):
    return client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"upload": (filename, payload, "image/png")},
        headers=headers,
    )


def test_attachment_validation_and_authorized_download(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"])
    stored = _upload(client, ticket["id"], customer)
    assert stored.status_code == 201, stored.text
    assert stored.json()["size_bytes"] == len(PNG_BYTES)
    rejected = client.post(
        f"/api/v1/tickets/{ticket['id']}/attachments",
        files={"upload": ("notes.txt", b"plain text is not evidence", "text/plain")},
        headers=customer,
    )
    assert rejected.status_code == 422, rejected.text
    oversized = client.post(
        f"/api/v1/tickets/{ticket['id']}/attachments",
        files={"upload": ("big.png", PNG_BYTES + b"\x00" * 5_000_000, "image/png")},
        headers=customer,
    )
    assert oversized.status_code == 413, oversized.text
    download = client.get(
        f"/api/v1/tickets/{ticket['id']}/attachments/{stored.json()['id']}", headers=customer
    )
    assert download.status_code == 200, download.text
    assert download.content == PNG_BYTES
    stranger = _customer(client, application, "stranger@example.com")
    leaked = client.get(
        f"/api/v1/tickets/{ticket['id']}/attachments/{stored.json()['id']}", headers=stranger
    )
    assert leaked.status_code == 404, leaked.text


def _run_full_ticket(client, application, email: str = "leela@example.com") -> dict:
    order, _ = _installed_order(client, application, email)
    customer = _login(client, "customer", email, "Solarops123")
    ticket = _create_ticket(client, customer, order["id"])
    _triage(client, ticket["id"])
    job = _repair_job(client, ticket["id"], _tech_id(application, "tech@example.com"))
    _record_full_repair(client, job["id"], _technician(client))
    ready = client.post(
        f"/api/v1/tickets/{ticket['id']}/resolution-ready",
        json={"summary": "Isolator replaced; generation verified at 2.9 kW under load."},
        headers=_support(client),
    )
    assert ready.status_code == 200, ready.text
    assert ready.json()["status"] == "resolved"
    assert ready.json()["resolution_version"] == 1
    return ticket


def test_leela_acceptance_flow_closes_and_persists(client, application):
    _all_staff(application)
    ticket = _run_full_ticket(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    summary = client.get(f"/api/v1/tickets/{ticket['id']}/resolution-summary", headers=customer)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["summary_version"] == 1
    assert body["summary"]["work_performed"]
    confirmed = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"decision": "confirmed", "summary_version": body["summary_version"]},
        headers=customer,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "customer_confirmed"
    closed = client.post(
        f"/api/v1/tickets/{ticket['id']}/close",
        json={"reason": "Customer confirmed; closing the ticket."},
        headers=_support(client),
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    client.post("/api/v1/auth/logout", headers=customer)
    fresh = _login(client, "customer", "leela@example.com", "Solarops123")
    mine = client.get("/api/v1/tickets", headers=fresh)
    assert mine.status_code == 200, mine.text
    assert [row["reference"] for row in mine.json()["items"]] == [closed.json()["reference"]]
    detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=fresh)
    assert detail.json()["status"] == "closed"
    actions = [event["action"] for event in
               client.get(f"/api/v1/tickets/{ticket['id']}/history", headers=fresh).json()]
    for expected in ("created", "triaged", "repair_job_created", "technician_arrived",
                     "diagnostics_recorded", "work_recorded", "work_submitted",
                     "resolution_ready", "resolution_confirmed", "closed"):
        assert expected in actions, actions


def test_support_cannot_confirm_and_replay_is_rejected(client, application):
    _all_staff(application)
    ticket = _run_full_ticket(client, application)
    support = _support(client)
    impersonated = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"decision": "confirmed", "summary_version": 1},
        headers=support,
    )
    assert impersonated.status_code == 403, impersonated.text
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    confirmed = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"decision": "confirmed", "summary_version": 1},
        headers=customer,
    )
    assert confirmed.status_code == 200, confirmed.text
    replay = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"decision": "confirmed", "summary_version": 1},
        headers=customer,
    )
    assert replay.status_code == 409, replay.text
    assert replay.json()["error"]["code"] in ("duplicate_confirmation", "invalid_transition")


def test_disputed_resolution_reopens_and_needs_new_version(client, application):
    _all_staff(application)
    ticket = _run_full_ticket(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    disputed = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"decision": "disputed", "summary_version": 1,
              "note": "Generation still drops out at noon."},
        headers=customer,
    )
    assert disputed.status_code == 200, disputed.text
    assert disputed.json()["status"] == "in_progress"
    blocked_close = client.post(
        f"/api/v1/tickets/{ticket['id']}/close",
        json={"reason": "Trying to close a disputed ticket."},
        headers=_support(client),
    )
    assert blocked_close.status_code == 409, blocked_close.text
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    stale = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"decision": "confirmed", "summary_version": 1},
        headers=customer,
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] in ("stale_summary", "invalid_transition")
    with Session(application.state.engine) as db:
        ack = db.scalar(
            select(ResolutionAcknowledgment).where(
                ResolutionAcknowledgment.ticket_id == uuid.UUID(ticket["id"]))
        )
        assert ack is not None and ack.decision == "disputed"


def test_stale_summary_rejected_after_new_version(client, application):
    _all_staff(application)
    ticket = _run_full_ticket(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    assert (
        client.post(
            f"/api/v1/tickets/{ticket['id']}/confirmation",
            json={"decision": "disputed", "summary_version": 1,
                  "note": "Still dropping out at noon."},
            headers=customer,
        ).status_code
        == 200
    )
    ready = client.post(
        f"/api/v1/tickets/{ticket['id']}/resolution-ready",
        json={"summary": "Re-torqued array connections; monitored a full sunny day."},
        headers=_support(client),
    )
    assert ready.status_code == 200, ready.text
    assert ready.json()["resolution_version"] == 2
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    stale = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"decision": "confirmed", "summary_version": 1},
        headers=customer,
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "stale_summary"


def test_reopen_closed_ticket(client, application):
    _all_staff(application)
    ticket = _run_full_ticket(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    assert (
        client.post(
            f"/api/v1/tickets/{ticket['id']}/confirmation",
            json={"decision": "confirmed", "summary_version": 1},
            headers=customer,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tickets/{ticket['id']}/close",
            json={"reason": "Customer confirmed; closing."},
            headers=_support(client),
        ).status_code
        == 200
    )
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    reopened = client.post(
        f"/api/v1/tickets/{ticket['id']}/reopen",
        json={"reason": "Fault E-07 is back a week later."},
        headers=customer,
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "in_progress"


def test_failed_confirmation_rolls_back(client, application):
    _all_staff(application)
    ticket = _run_full_ticket(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    rejected = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"decision": "disputed", "summary_version": 1, "note": "x"},
        headers=customer,
    )
    assert rejected.status_code == 422, rejected.text
    detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=customer)
    assert detail.json()["status"] == "resolved"
    assert detail.json()["acknowledgments"] == []
    with Session(application.state.engine) as db:
        count = db.scalar(
            select(func.count()).select_from(ResolutionAcknowledgment).where(
                ResolutionAcknowledgment.ticket_id == uuid.UUID(ticket["id"]))
        )
        assert count == 0


def test_concurrent_confirmation_has_single_winner(client, application):
    from app.services import ticket_service

    _all_staff(application)
    ticket = _run_full_ticket(client, application)
    with Session(application.state.engine) as db:
        customer = db.scalar(select(User).where(User.email == "leela@example.com"))
        assert customer is not None
        customer_id = customer.id
    barrier = threading.Barrier(2)
    results: list[str] = []

    def _race() -> None:
        session = application.state.session_factory()
        try:
            user = session.get(User, customer_id)
            assert user is not None
            barrier.wait()
            ticket_service.confirm_resolution(
                session, user, uuid.UUID(ticket["id"]), "confirmed", 1, None)
            session.commit()
            results.append("ok")
        except AppError as exc:
            session.rollback()
            results.append(exc.code)
        except IntegrityError:
            session.rollback()
            results.append("integrity_conflict")
        finally:
            session.close()

    threads = [threading.Thread(target=_race), threading.Thread(target=_race)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) in (
        ["duplicate_confirmation", "ok"],
        ["integrity_conflict", "ok"],
        ["invalid_transition", "ok"],
    ), results
    with Session(application.state.engine) as db:
        count = db.scalar(
            select(func.count()).select_from(ResolutionAcknowledgment).where(
                ResolutionAcknowledgment.ticket_id == uuid.UUID(ticket["id"]))
        )
        assert count == 1
        row = db.scalar(select(ServiceTicket).where(ServiceTicket.id == uuid.UUID(ticket["id"])))
        assert row is not None and row.status == "customer_confirmed"


def test_cancel_before_work_and_info_roundtrip(client, application):
    _all_staff(application)
    order, _ = _installed_order(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    ticket = _create_ticket(client, customer, order["id"])
    cancelled = client.post(
        f"/api/v1/tickets/{ticket['id']}/cancel",
        json={"reason": "The inverter started working again."},
        headers=customer,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    second = _create_ticket(client, customer, order["id"])
    _triage(client, second["id"])
    asked = client.post(
        f"/api/v1/tickets/{second['id']}/request-info",
        json={"message": "Which string shows the fault: east or west?"},
        headers=_support(client),
    )
    assert asked.json()["status"] == "waiting_customer"
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    replied = client.post(
        f"/api/v1/tickets/{second['id']}/customer-reply",
        json={"message": "The east string shows E-07."},
        headers=customer,
    )
    assert replied.status_code == 200, replied.text
    assert replied.json()["status"] == "triaged"
    escalated = client.post(
        f"/api/v1/tickets/{second['id']}/escalation",
        json={"reason": "Second E-07 this month.", "verified_priority": "critical"},
        headers=_support(client),
    )
    assert escalated.status_code == 200, escalated.text
    assert escalated.json()["escalated"] is True
    assert escalated.json()["verified_priority"] == "critical"


def test_support_staff_directory_lists_eligible_technicians(client, application):
    _all_staff(application)
    support = _support(client)
    technicians = client.get("/api/v1/support/staff?role=technician", headers=support)
    assert technicians.status_code == 200, technicians.text
    codes = {row["employee_code"] for row in technicians.json()}
    assert {"EMP-TECH-901", "EMP-TECH-902"} <= codes
    owners = client.get("/api/v1/support/staff?role=support", headers=support)
    assert owners.status_code == 200, owners.text
    assert [row["employee_code"] for row in owners.json()] == ["EMP-SUP-901"]
    customer = _customer(client, application, "nosy@example.com")
    assert client.get("/api/v1/support/staff", headers=customer).status_code == 403

