"""Customer enquiry through confirmed order, against PostgreSQL."""

import threading
import uuid
from datetime import timedelta

from app.core.errors import AppError
from app.core.security import hash_password, utcnow
from app.models.identity import EmployeeProfile, User
from app.models.workflow import (
    InstallationSchedulingRequest,
    Quotation,
    QuotationLine,
    SalesOrder,
    Survey,
    WarehousePreparationRequest,
)
from app.services.order_service import confirm_order
from app.services.quotation_service import accept_quotation
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers, login, signup_and_verify

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

JPEG = b"\xff\xd8\xff\x00solarops-test"


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


def _enquiry(client, headers: dict[str, str], body: dict | None = None) -> dict:
    created = client.post(
        "/api/v1/enquiries",
        json=body or ENQUIRY,
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert created.status_code == 201, created.text
    return created.json()


def _sales(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-SALES-901", "Staffpass123")


def _technician(client) -> dict[str, str]:
    return _login(client, "employee", "EMP-TECH-901", "Staffpass123")


def _qualify(client, enquiry_id: str) -> None:
    sales = _sales(client)
    response = client.patch(
        f"/api/v1/enquiries/{enquiry_id}/qualification",
        json={
            "status": "under_review",
            "note": "Checking the roof.",
        },
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
    assert qualified.json()["decision_by_user_id"]
    assert qualified.json()["grid_connection_suitable"] is True


def _survey_to_approved(client, application, enquiry_id: str, cable: str = "25.00") -> dict:
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
    assert assigned.json()["appointment_status"] == "pending"
    assert assigned.json()["appointment_starts_at"] is None
    technician = _technician(client)
    started = client.post(f"/api/v1/surveys/{survey_id}/start", headers=technician)
    assert started.status_code == 200, started.text
    submitted = client.post(
        f"/api/v1/surveys/{survey_id}/submission",
        json={
            "azimuth_deg": "180.00",
            "tilt_deg": "12.50",
            "shadow_free_area_sqm": "38.25",
            "cable_distance_m": cable,
            "grid_connection": "suitable",
            "notes": "South-facing roof with a short cable run.",
        },
        headers=technician,
    )
    assert submitted.status_code == 200, submitted.text
    sales = _sales(client)
    approved = client.post(
        f"/api/v1/surveys/{survey_id}/approval",
        json={"decision": "approved", "note": "Measurements accepted."},
        headers=sales,
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


def _quote(client, survey_id: str, package: str = "PKG-ONG-3") -> dict:
    sales = _sales(client)
    response = client.post(
        "/api/v1/quotations",
        json={"survey_id": survey_id, "package_code": package, "discount_minor": 0},
        headers={**sales, "Idempotency-Key": uuid.uuid4().hex},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_unqualified_enquiry_cannot_be_surveyed(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    sales = _sales(client)
    denied = client.post("/api/v1/surveys", json={"enquiry_id": enquiry["id"]}, headers=sales)
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "enquiry_not_qualified"


def test_qualification_requires_roof_and_grid(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    sales = _sales(client)
    client.patch(
        f"/api/v1/enquiries/{enquiry['id']}/qualification",
        json={"status": "under_review"},
        headers=sales,
    )
    missing = client.patch(
        f"/api/v1/enquiries/{enquiry['id']}/qualification",
        json={"status": "qualified", "note": "Looks fine."},
        headers=sales,
    )
    assert missing.status_code == 422


def test_only_assigned_technician_submits_and_bad_measurements_fail(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    _staff(application, "technician", "other-tech@example.com", "EMP-TECH-902")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    sales = _sales(client)
    survey = client.post("/api/v1/surveys", json={"enquiry_id": enquiry["id"]}, headers=sales).json()
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        assert tech is not None
        tech_id = str(tech.id)
    client.post(
        f"/api/v1/surveys/{survey['id']}/assignment",
        json={"technician_user_id": tech_id},
        headers=sales,
    )
    technician = _technician(client)
    client.post(f"/api/v1/surveys/{survey['id']}/start", headers=technician)
    other = _login(client, "employee", "EMP-TECH-902", "Staffpass123")
    stolen = client.post(
        f"/api/v1/surveys/{survey['id']}/submission",
        json={
            "azimuth_deg": "10",
            "tilt_deg": "10",
            "shadow_free_area_sqm": "20",
            "cable_distance_m": "10",
            "grid_connection": "suitable",
            "notes": "Not my survey.",
        },
        headers=other,
    )
    assert stolen.status_code == 403
    technician = _technician(client)
    invalid = client.post(
        f"/api/v1/surveys/{survey['id']}/submission",
        json={
            "azimuth_deg": "400",
            "tilt_deg": "10",
            "shadow_free_area_sqm": "20",
            "cable_distance_m": "10",
            "grid_connection": "suitable",
            "notes": "Bad azimuth.",
        },
        headers=technician,
    )
    assert invalid.status_code == 422
    negative = client.post(
        f"/api/v1/surveys/{survey['id']}/submission",
        json={
            "azimuth_deg": "10",
            "tilt_deg": "-1",
            "shadow_free_area_sqm": "20",
            "cable_distance_m": "10",
            "grid_connection": "suitable",
            "notes": "Negative tilt.",
        },
        headers=technician,
    )
    assert negative.status_code == 422


def test_rejected_survey_cannot_be_quoted_and_resurvey_keeps_history(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    sales = _sales(client)
    survey = client.post("/api/v1/surveys", json={"enquiry_id": enquiry["id"]}, headers=sales).json()
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        assert tech is not None
        tech_id = str(tech.id)
    client.post(
        f"/api/v1/surveys/{survey['id']}/assignment",
        json={"technician_user_id": tech_id},
        headers=sales,
    )
    technician = _technician(client)
    client.post(f"/api/v1/surveys/{survey['id']}/start", headers=technician)
    client.post(
        f"/api/v1/surveys/{survey['id']}/submission",
        json={
            "azimuth_deg": "90",
            "tilt_deg": "10",
            "shadow_free_area_sqm": "20",
            "cable_distance_m": "15",
            "grid_connection": "unsuitable",
            "notes": "Tree shade across the roof.",
        },
        headers=technician,
    )
    sales = _sales(client)
    rejected = client.post(
        f"/api/v1/surveys/{survey['id']}/approval",
        json={"decision": "rejected", "note": "Measure again after pruning."},
        headers=sales,
    )
    assert rejected.status_code == 200
    quoted = client.post(
        "/api/v1/quotations",
        json={"survey_id": survey["id"], "package_code": "PKG-ONG-3"},
        headers={**sales, "Idempotency-Key": "quote-reject-001"},
    )
    assert quoted.status_code == 409
    assert quoted.json()["error"]["code"] == "survey_not_approved"
    resurvey = client.post(f"/api/v1/surveys/{survey['id']}/resurvey", headers=sales)
    assert resurvey.status_code == 201, resurvey.text
    assert resurvey.json()["revision_of_survey_id"] == survey["id"]
    assert resurvey.json()["status"] == "draft"
    with Session(application.state.engine) as db:
        original = db.get(Survey, uuid.UUID(survey["id"]))
        assert original is not None
        assert original.status == "rejected"


def test_approved_survey_quotes_exact_bom_and_total(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"], cable="36.00")
    sales = _sales(client)
    template = client.get("/api/v1/packages/PKG-ONG-3/versions/current", headers=sales)
    assert template.status_code == 200, template.text
    quote = _quote(client, survey["id"])
    materials = [line for line in quote["lines"] if line["line_kind"] == "material"]
    panels = next(line for line in materials if line["component_code"] == "PANEL-550")
    wiring = next(line for line in materials if line["component_code"] == "WIRE-BUNDLE")
    assert panels["quantity"] == 6
    assert wiring["quantity"] == 4
    material_total = sum(line["line_total_minor"] for line in materials)
    installation = sum(
        line["line_total_minor"] for line in quote["lines"] if line["line_kind"] == "installation"
    )
    taxable = material_total - quote["discount_minor"] + installation
    tax = (taxable * quote["tax_rate_bps"] + 5000) // 10000
    assert quote["material_total_minor"] == material_total
    assert quote["tax_minor"] == tax
    assert quote["total_minor"] == taxable + tax
    assert quote["tax_rate_bps"] == 1800
    assert "Demonstration tax" in quote["lines"][-1]["description"]
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    requirement = client.get(
        f"/api/v1/quotations/{quote['id']}/payment-requirement", headers=customer
    )
    assert requirement.status_code == 200
    assert requirement.json()["minimum_advance_minor"] == quote["total_minor"] * 40 // 100
    assert requirement.json()["verified_minor"] == 0


def test_revision_history_acceptance_and_foreign_customer(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    first = _quote(client, survey["id"])
    first_panel = next(line["line_total_minor"] for line in first["lines"] if line["component_code"] == "PANEL-550")
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    change = client.post(
        f"/api/v1/quotations/{first['id']}/revision-requests",
        json={"category": "pricing", "request_text": "Please explain the inverter price."},
        headers=customer,
    )
    assert change.status_code == 201, change.text
    sales = _sales(client)
    revised = client.post(
        f"/api/v1/quotations/{first['id']}/revisions",
        json={
            "package_code": "PKG-ONG-3",
            "discount_minor": 0,
            "revision_request_id": change.json()["id"],
        },
        headers={**sales, "Idempotency-Key": "quote-revision-01"},
    )
    assert revised.status_code == 201, revised.text
    assert revised.json()["version_number"] == 2
    assert revised.json()["supersedes_quotation_id"] == first["id"]
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    with Session(application.state.engine) as db:
        old_panel = db.scalar(
            select(QuotationLine).where(
                QuotationLine.quotation_id == uuid.UUID(first["id"]),
                QuotationLine.component_code == "PANEL-550",
            )
        )
        old = db.get(Quotation, uuid.UUID(first["id"]))
        assert old is not None and old.status == "superseded"
        assert old_panel is not None and old_panel.line_total_minor == first_panel
    stale = client.post(f"/api/v1/quotations/{first['id']}/acceptance", headers=customer)
    assert stale.status_code == 409
    _customer(client, application, "other@example.com")
    other = _login(client, "customer", "other@example.com", "Solarops123")
    foreign = client.post(f"/api/v1/quotations/{revised.json()['id']}/acceptance", headers=other)
    assert foreign.status_code == 404
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    accepted = client.post(f"/api/v1/quotations/{revised.json()['id']}/acceptance", headers=customer)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    again = client.post(f"/api/v1/quotations/{revised.json()['id']}/acceptance", headers=customer)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "already_accepted"


def test_unverified_payment_blocks_order_and_sandbox_is_test_only(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    _staff(application, "warehouse_staff", "wh@example.com", "EMP-WH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    quote = _quote(client, survey["id"])
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    accepted = client.post(f"/api/v1/quotations/{quote['id']}/acceptance", headers=customer)
    assert accepted.status_code == 200, accepted.text
    sales = _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    blocked = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**sales, "Idempotency-Key": "order-before-pay"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "payment_not_verified"
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    intent = client.post(
        "/api/v1/payments/intents",
        json={"quotation_id": quote["id"], "amount_minor": quote["total_minor"]},
        headers={**customer, "Idempotency-Key": "pay-sandbox-0001"},
    )
    assert intent.status_code == 201, intent.text
    assert intent.json()["is_test_only"] is True
    assert intent.json()["status"] == "pending"
    sales = _sales(client)
    still_blocked = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**sales, "Idempotency-Key": "order-pending-pay"},
    )
    assert still_blocked.status_code == 409
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    unknown = client.post(
        f"/api/v1/payments/intents/{intent.json()['id']}/sandbox-outcome",
        json={"outcome": "unknown"},
        headers=customer,
    )
    assert unknown.status_code == 200
    assert unknown.json()["status"] == "unresolved"
    assert unknown.json()["is_test_only"] is True
    second = client.post(
        "/api/v1/payments/intents",
        json={"quotation_id": quote["id"], "amount_minor": quote["total_minor"]},
        headers={**customer, "Idempotency-Key": "pay-sandbox-0002"},
    )
    verified = client.post(
        f"/api/v1/payments/intents/{second.json()['id']}/sandbox-outcome",
        json={"outcome": "succeeded"},
        headers=customer,
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "verified"
    assert verified.json()["is_test_only"] is True
    assert verified.json()["provider"] == "sandbox"
    replay = client.post(
        "/api/v1/payments/intents",
        json={"quotation_id": quote["id"], "amount_minor": quote["total_minor"]},
        headers={**customer, "Idempotency-Key": "pay-sandbox-0002"},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == second.json()["id"]
    denied = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**customer, "Idempotency-Key": "customer-cannot-order"},
    )
    assert denied.status_code == 403
    sales = _sales(client)
    created = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**sales, "Idempotency-Key": "order-confirm-001"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["quotation_version"] == 1
    assert body["status"] == "confirmed"
    assert body["test_only_payment"] is True
    assert body["payment_verification_state"] == "test_verified"
    assert body["template_version_id"] == quote["template_version_id"]
    panel = next(line for line in body["lines"] if line["component_code"] == "PANEL-550")
    assert panel["quantity"] == 6
    again = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**sales, "Idempotency-Key": "order-confirm-001"},
    )
    assert again.status_code == 200
    assert again.json()["id"] == body["id"]
    duplicate = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**sales, "Idempotency-Key": "order-confirm-002"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_order"
    warehouse = _login(client, "employee", "EMP-WH-901", "Staffpass123")
    queue = client.get("/api/v1/warehouse/preparation", headers=warehouse)
    assert queue.status_code == 200, queue.text
    assert queue.json()[0]["order_id"] == body["id"]
    assert queue.json()[0]["status"] == "pending_preparation"
    assert any(line["component_code"] == "PANEL-550" and line["quantity"] == 6 for line in queue.json()[0]["lines"])
    hidden = client.get("/api/v1/scheduling/installations", headers=warehouse)
    assert hidden.status_code == 403
    sales = _sales(client)
    schedule = client.get("/api/v1/scheduling/installations", headers=sales)
    assert schedule.status_code == 200
    assert schedule.json()[0]["status"] == "unscheduled"
    assert schedule.json()[0]["slot_starts_at"] is None
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    customer_queue = client.get("/api/v1/warehouse/preparation", headers=customer)
    assert customer_queue.status_code == 403


def test_cash_receipt_is_not_a_sandbox_payment(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    quote = _quote(client, survey["id"])
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    client.post(f"/api/v1/quotations/{quote['id']}/acceptance", headers=customer)
    fake = client.post(
        "/api/v1/payments/cash-receipts",
        json={
            "quotation_id": quote["id"],
            "amount_minor": quote["total_minor"],
            "receipt_reference": "CASH-100",
        },
        headers={**customer, "Idempotency-Key": "cash-by-customer"},
    )
    assert fake.status_code == 403
    sales = _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    receipt = client.post(
        "/api/v1/payments/cash-receipts",
        json={
            "quotation_id": quote["id"],
            "amount_minor": quote["total_minor"],
            "receipt_reference": "CASH-100",
        },
        headers={**sales, "Idempotency-Key": "cash-receipt-001"},
    )
    assert receipt.status_code == 201, receipt.text
    assert receipt.json()["is_test_only"] is False
    assert receipt.json()["status"] == "verified"
    assert receipt.json()["provider"] == "cash_receipt"
    order = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**sales, "Idempotency-Key": "order-cash-0001"},
    )
    assert order.status_code == 201, order.text
    assert order.json()["payment_verification_state"] == "manually_verified"
    assert order.json()["test_only_payment"] is False


def test_downstream_qualification_does_not_rewrite_survey(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    sales = _sales(client)
    locked = client.patch(
        f"/api/v1/enquiries/{enquiry['id']}/qualification",
        json={
            "status": "under_review",
            "note": "Area revised.",
            "shadow_free_area_sqm": "55.00",
            "grid_connection_suitable": True,
        },
        headers=sales,
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "qualification_locked"
    with Session(application.state.engine) as db:
        row = db.get(Survey, uuid.UUID(survey["id"]))
        assert row is not None and row.status == "approved"
        assert str(row.shadow_free_area_sqm) == "38.25"


def test_expired_and_withdrawn_quotations_cannot_be_accepted(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    quote = _quote(client, survey["id"])
    with Session(application.state.engine) as db:
        row = db.get(Quotation, uuid.UUID(quote["id"]))
        assert row is not None
        row.expires_at = utcnow() - timedelta(days=1)
        db.commit()
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    expired = client.post(f"/api/v1/quotations/{quote['id']}/acceptance", headers=customer)
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "quotation_expired"
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    second_enquiry = _enquiry(client, customer)
    _qualify(client, second_enquiry["id"])
    second_survey = _survey_to_approved(client, application, second_enquiry["id"])
    second = _quote(client, second_survey["id"])
    sales = _sales(client)
    withdrawn = client.post(f"/api/v1/quotations/{second['id']}/withdrawal", headers=sales)
    assert withdrawn.status_code == 200
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    denied = client.post(f"/api/v1/quotations/{second['id']}/acceptance", headers=customer)
    assert denied.status_code == 409


def test_failed_order_transaction_rolls_back(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    quote = _quote(client, survey["id"])
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    client.post(f"/api/v1/quotations/{quote['id']}/acceptance", headers=customer)
    sales = _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    client.post(
        "/api/v1/payments/cash-receipts",
        json={
            "quotation_id": quote["id"],
            "amount_minor": quote["total_minor"],
            "receipt_reference": "CASH-ROLLBACK",
        },
        headers={**sales, "Idempotency-Key": "cash-rollback-01"},
    )
    with Session(application.state.engine) as db:
        actor = db.scalar(select(User).where(User.email == "sales@example.com"))
        assert actor is not None
        actor_id = actor.id
    session = application.state.session_factory()
    try:
        actor = session.get(User, actor_id)
        assert actor is not None
        confirm_order(session, actor, uuid.UUID(quote["id"]), "order-rollback-01")
        raise RuntimeError("injected failure before commit")
    except RuntimeError:
        session.rollback()
    finally:
        session.close()
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(SalesOrder)) == 0
        assert db.scalar(select(func.count()).select_from(WarehousePreparationRequest)) == 0
        assert db.scalar(select(func.count()).select_from(InstallationSchedulingRequest)) == 0
    sales = _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    created = client.post(
        "/api/v1/orders",
        json={"quotation_id": quote["id"]},
        headers={**sales, "Idempotency-Key": "order-after-rollback"},
    )
    assert created.status_code == 201, created.text


def test_concurrent_acceptance_and_order_confirmation(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    _qualify(client, enquiry["id"])
    survey = _survey_to_approved(client, application, enquiry["id"])
    quote = _quote(client, survey["id"])
    with Session(application.state.engine) as db:
        owner = db.scalar(select(User).where(User.email == "leela@example.com"))
        actor = db.scalar(select(User).where(User.email == "sales@example.com"))
        assert owner is not None and actor is not None
        owner_id = owner.id
        actor_id = actor.id
    barrier = threading.Barrier(2)
    results: list[str] = []

    def accept() -> None:
        session = application.state.session_factory()
        try:
            user = session.get(User, owner_id)
            assert user is not None
            barrier.wait()
            accept_quotation(session, user, uuid.UUID(quote["id"]))
            session.commit()
            results.append("ok")
        except AppError as exc:
            session.rollback()
            results.append(exc.code)
        finally:
            session.close()

    threads = [threading.Thread(target=accept), threading.Thread(target=accept)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["already_accepted", "ok"]

    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    sales = _login(client, "employee", "EMP-SALES-901", "Staffpass123")
    paid = client.post(
        "/api/v1/payments/cash-receipts",
        json={
            "quotation_id": quote["id"],
            "amount_minor": quote["total_minor"],
            "receipt_reference": "CASH-RACE",
        },
        headers={**sales, "Idempotency-Key": "cash-race-0001"},
    )
    assert paid.status_code == 201, paid.text
    order_results: list[str] = []
    order_barrier = threading.Barrier(2)

    def confirm(key: str) -> None:
        session = application.state.session_factory()
        try:
            user = session.get(User, actor_id)
            assert user is not None
            order_barrier.wait()
            confirm_order(session, user, uuid.UUID(quote["id"]), key)
            session.commit()
            order_results.append("ok")
        except AppError as exc:
            session.rollback()
            order_results.append(exc.code)
        finally:
            session.close()

    racers = [
        threading.Thread(target=confirm, args=("order-race-0001",)),
        threading.Thread(target=confirm, args=("order-race-0002",)),
    ]
    for thread in racers:
        thread.start()
    for thread in racers:
        thread.join()
    assert sorted(order_results) == ["duplicate_order", "ok"]
    with Session(application.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(SalesOrder)) == 1


def test_evidence_upload_and_role_guards(client, application):
    _staff(application, "sales", "sales@example.com", "EMP-SALES-901")
    _staff(application, "technician", "tech@example.com", "EMP-TECH-901")
    _staff(application, "admin", "admin@example.com", "EMP-ADMIN-901")
    customer = _customer(client, application)
    enquiry = _enquiry(client, customer)
    forbidden = client.post("/api/v1/surveys", json={"enquiry_id": enquiry["id"]}, headers=customer)
    assert forbidden.status_code == 403
    _qualify(client, enquiry["id"])
    sales = _sales(client)
    survey = client.post("/api/v1/surveys", json={"enquiry_id": enquiry["id"]}, headers=sales).json()
    with Session(application.state.engine) as db:
        tech = db.scalar(select(User).where(User.email == "tech@example.com"))
        assert tech is not None
        tech_id = str(tech.id)
    client.post(
        f"/api/v1/surveys/{survey['id']}/assignment",
        json={"technician_user_id": tech_id},
        headers=sales,
    )
    technician = _technician(client)
    uploaded = client.post(
        f"/api/v1/surveys/{survey['id']}/evidence",
        files={"upload": ("roof.jpg", JPEG, "image/jpeg")},
        headers=technician,
    )
    assert uploaded.status_code == 201, uploaded.text
    downloaded = client.get(
        f"/api/v1/surveys/{survey['id']}/evidence/{uploaded.json()['id']}",
        headers=technician,
    )
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"\xff\xd8\xff")
    text_file = client.post(
        f"/api/v1/surveys/{survey['id']}/evidence",
        files={"upload": ("notes.txt", b"hello", "text/plain")},
        headers=technician,
    )
    assert text_file.status_code == 422
    approval = client.post(
        f"/api/v1/surveys/{survey['id']}/approval",
        json={"decision": "approved"},
        headers=technician,
    )
    assert approval.status_code == 403
