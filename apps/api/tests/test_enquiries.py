"""Enquiry workflow tests. Customer and sales are different database users."""

import uuid

import pytest
from app.core.security import hash_password, utcnow
from app.models.audit import AuditEvent
from app.models.enquiry import Enquiry, EnquiryStatusHistory
from app.models.identity import EmployeeProfile, User
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


def _sales_user(application) -> None:
    with Session(application.state.engine) as db:
        user = User(
            email="sales@example.com",
            password_hash=hash_password("Salespass123"),
            role_code="sales",
            email_verified_at=utcnow(),
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(
            EmployeeProfile(
                user_id=user.id,
                employee_code="EMP-SALES-901",
                full_name="Sales Person",
                phone="9845000001",
            )
        )
        db.commit()


def _customer_headers(client, application) -> dict[str, str]:
    signup_and_verify(client, application, "leela@example.com")
    signed_in = login(
        client, kind="customer", identifier="leela@example.com", password="Solarops123"
    )
    assert signed_in.status_code == 200, signed_in.text
    return csrf_headers(client)


def test_valid_enquiry_persists(client, application):
    headers = _customer_headers(client, application)
    key = "enquiry-key-0001"
    created = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={**headers, "Idempotency-Key": key},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["reference"].startswith("ENQ-")
    assert body["status"] == "submitted"
    assert body["monthly_bill_minor"] == 450000
    assert body["preferred_capacity_w"] == 3000
    with Session(application.state.engine) as db:
        row = db.query(Enquiry).one()
        assert row.reference == body["reference"]
        assert row.monthly_bill_minor == 450000
        history = db.query(EnquiryStatusHistory).one()
        assert history.to_status == "submitted"
        audit = db.query(AuditEvent).filter_by(action="enquiry.created").one()
        assert audit.entity_id == row.id


def test_invalid_enquiry_rejected(client, application):
    headers = _customer_headers(client, application)
    payload = {**ENQUIRY, "preferred_capacity_w": 1500, "monthly_bill_minor": -1}
    response = client.post(
        "/api/v1/enquiries",
        json=payload,
        headers={**headers, "Idempotency-Key": "enquiry-key-0002"},
    )
    assert response.status_code == 422
    with Session(application.state.engine) as db:
        assert db.query(Enquiry).count() == 0


def test_duplicate_submission_is_idempotent(client, application):
    headers = _customer_headers(client, application)
    first = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={**headers, "Idempotency-Key": "same-key-0001"},
    )
    second = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={**headers, "Idempotency-Key": "same-key-0001"},
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    changed = {**ENQUIRY, "subsidy_interest": False}
    conflict = client.post(
        "/api/v1/enquiries",
        json=changed,
        headers={**headers, "Idempotency-Key": "same-key-0001"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    with Session(application.state.engine) as db:
        assert db.query(Enquiry).count() == 1


def test_customer_cannot_read_another_customers_enquiry(client, application):
    headers = _customer_headers(client, application)
    created = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={**headers, "Idempotency-Key": "owner-key-0001"},
    )
    enquiry_id = created.json()["id"]
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    signup_and_verify(client, application, "other@example.com")
    login(client, kind="customer", identifier="other@example.com", password="Solarops123")
    hidden = client.get(f"/api/v1/enquiries/{enquiry_id}")
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "not_found"
    listing = client.get("/api/v1/enquiries")
    assert listing.status_code == 200
    assert listing.json()["total"] == 0


def test_sales_can_read_and_qualify_and_invalid_transition_fails(client, application):
    headers = _customer_headers(client, application)
    created = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={**headers, "Idempotency-Key": "sales-key-0001"},
    )
    enquiry_id = created.json()["id"]
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))

    denied = client.patch(
        f"/api/v1/enquiries/{enquiry_id}/qualification",
        json={"status": "qualified", "note": "Looks suitable."},
        headers=csrf_headers(client),
    )
    assert denied.status_code == 401

    _sales_user(application)
    signed_in = login(client, kind="employee", identifier="EMP-SALES-901", password="Salespass123")
    assert signed_in.status_code == 200, signed_in.text
    assert signed_in.json()["user"]["role"] == "sales"
    listed = client.get("/api/v1/enquiries")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["reference"] == created.json()["reference"]

    updated = client.patch(
        f"/api/v1/enquiries/{enquiry_id}/qualification",
        json={"status": "under_review", "note": "Called the customer."},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "under_review"
    invalid = client.patch(
        f"/api/v1/enquiries/{enquiry_id}/qualification",
        json={"status": "under_review"},
        headers=csrf_headers(client),
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "invalid_transition"

    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    login(client, kind="customer", identifier="leela@example.com", password="Solarops123")
    visible = client.get(f"/api/v1/enquiries/{enquiry_id}")
    assert visible.status_code == 200
    assert visible.json()["status"] == "under_review"
    assert visible.json()["history"][-1]["to_status"] == "under_review"

    with Session(application.state.engine) as db:
        history = (
            db.query(EnquiryStatusHistory)
            .filter(EnquiryStatusHistory.enquiry_id == uuid.UUID(enquiry_id))
            .order_by(EnquiryStatusHistory.created_at)
            .all()
        )
        assert [row.to_status for row in history] == ["submitted", "under_review"]
        audits = db.query(AuditEvent).filter_by(action="enquiry.qualification_updated").count()
        assert audits == 1


def test_customer_cannot_open_staff_qualification(client, application):
    headers = _customer_headers(client, application)
    created = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={**headers, "Idempotency-Key": "staff-key-0001"},
    )
    response = client.patch(
        f"/api/v1/enquiries/{created.json()['id']}/qualification",
        json={"status": "qualified"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 403


def test_malformed_uuid_and_unknown_route_errors(client, application):
    _customer_headers(client, application)
    response = client.get("/api/v1/enquiries/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    missing = client.get("/api/v1/does-not-exist")
    assert missing.status_code == 404


def test_packages_come_from_database(client, application):
    _customer_headers(client, application)
    response = client.get("/api/v1/packages")
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "PKG-ONG-3" in codes
    assert "PKG-OFG-1" in codes
    assert all("price" not in item for item in response.json())
