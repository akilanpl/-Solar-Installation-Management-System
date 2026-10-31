"""Constraint enforcement and rollback against migrated PostgreSQL, never SQLite."""

import uuid

import pytest
from app.models.enquiry import Enquiry
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers, login, signup_and_verify
from tests.test_enquiries import ENQUIRY, _customer_headers

pytestmark = pytest.mark.database


@pytest.mark.parametrize(
    "column,value",
    [
        ("monthly_bill_minor", -1),
        ("preferred_capacity_w", 1500),
        ("status", "invented"),
        ("site_id", uuid.UUID(int=0)),
    ],
)
def test_constraint_failure_rolls_back_without_damaging_saved_enquiry(
    client, application, column, value
):
    headers = _customer_headers(client, application)
    created = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={**headers, "Idempotency-Key": "constraint-test-key"},
    )
    assert created.status_code == 201, created.text
    enquiry_id = uuid.UUID(created.json()["id"])
    with Session(application.state.engine) as db:
        row = db.get(Enquiry, enquiry_id)
        original = getattr(row, column)
        setattr(row, column, value)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert getattr(db.get(Enquiry, enquiry_id), column) == original
        assert db.scalar(text("SELECT count(*) FROM enquiry_status_history")) == 1
    assert client.get(f"/api/v1/enquiries/{enquiry_id}").status_code == 200


def test_logout_revokes_captured_cookie_not_just_browser_cookie(client, application):
    signup_and_verify(client, application)
    response = login(
        client, kind="customer", identifier="customer@example.com", password="Solarops123"
    )
    assert response.status_code == 200
    captured = client.cookies.get("solarops_session")
    assert captured
    assert client.post("/api/v1/auth/logout", headers=csrf_headers(client)).status_code == 204
    client.cookies.set("solarops_session", captured)
    assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize(
    "endpoint,body,limit_setting",
    [
        (
            "login",
            {"account_kind": "customer", "identifier": "nobody@example.com", "password": "wrong"},
            "login_ip_limit",
        ),
        ("verify-email", {"email": "nobody@example.com", "code": "123456"}, "otp_attempt_limit"),
    ],
)
def test_auth_endpoint_rate_limits(client, application, monkeypatch, endpoint, body, limit_setting):
    monkeypatch.setattr(application.state.settings, limit_setting, 1)
    headers = csrf_headers(client)
    first = client.post(f"/api/v1/auth/{endpoint}", json=body, headers=headers)
    assert first.status_code in {400, 401}
    limited = client.post(f"/api/v1/auth/{endpoint}", json=body, headers=headers)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
