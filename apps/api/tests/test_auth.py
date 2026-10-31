"""Authentication behavior backed by PostgreSQL."""

from datetime import timedelta

from app.core.security import utcnow
from app.models.identity import EmailVerificationChallenge, User
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers, login, signup_and_verify


def test_valid_signup(client, application):
    response = client.post(
        "/api/v1/auth/signup",
        headers=csrf_headers(client),
        json={
            "full_name": "Leela Nair",
            "email": "leela@example.com",
            "phone": "9845012345",
            "password": "Solarops123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "leela@example.com"
    assert body["email_verified"] is False
    assert "code" not in response.text
    with Session(application.state.engine) as db:
        user = db.query(User).filter(User.email == "leela@example.com").one()
        challenge = db.query(EmailVerificationChallenge).filter_by(user_id=user.id).one()
        assert challenge.code_hash != application.state.email_sender.messages[-1].code
        assert application.state.email_sender.messages[-1].code not in challenge.code_hash


def test_duplicate_email_rejected(client, application):
    signup_and_verify(client, application, "dup@example.com")
    response = client.post(
        "/api/v1/auth/signup",
        headers=csrf_headers(client),
        json={
            "full_name": "Someone Else",
            "email": "dup@example.com",
            "phone": "9845011111",
            "password": "Solarops123",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_invalid_registration_rejected(client):
    response = client.post(
        "/api/v1/auth/signup",
        headers=csrf_headers(client),
        json={
            "full_name": "A",
            "email": "not-an-email",
            "phone": "123",
            "password": "short",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unverified_account_cannot_login(client, application):
    client.post(
        "/api/v1/auth/signup",
        headers=csrf_headers(client),
        json={
            "full_name": "Leela Nair",
            "email": "pending@example.com",
            "phone": "9845012345",
            "password": "Solarops123",
        },
    )
    response = login(
        client, kind="customer", identifier="pending@example.com", password="Solarops123"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "email_not_verified"
    assert "solarops_session" not in response.cookies


def test_invalid_otp_fails(client, application):
    client.post(
        "/api/v1/auth/signup",
        headers=csrf_headers(client),
        json={
            "full_name": "Leela Nair",
            "email": "otp@example.com",
            "phone": "9845012345",
            "password": "Solarops123",
        },
    )
    response = client.post(
        "/api/v1/auth/verify-email",
        headers=csrf_headers(client),
        json={"email": "otp@example.com", "code": "000000"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_verification_code"
    with Session(application.state.engine) as db:
        challenge = db.query(EmailVerificationChallenge).one()
        assert challenge.attempt_count == 1
        assert challenge.consumed_at is None


def test_expired_and_reused_otp_fail(client, application):
    client.post(
        "/api/v1/auth/signup",
        headers=csrf_headers(client),
        json={
            "full_name": "Leela Nair",
            "email": "expire@example.com",
            "phone": "9845012345",
            "password": "Solarops123",
        },
    )
    code = application.state.email_sender.messages[-1].code
    with Session(application.state.engine) as db:
        challenge = db.query(EmailVerificationChallenge).one()
        challenge.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    expired = client.post(
        "/api/v1/auth/verify-email",
        headers=csrf_headers(client),
        json={"email": "expire@example.com", "code": code},
    )
    assert expired.status_code == 400

    client.post(
        "/api/v1/auth/resend-verification",
        headers=csrf_headers(client),
        json={"email": "expire@example.com"},
    )
    fresh = application.state.email_sender.messages[-1].code
    ok = client.post(
        "/api/v1/auth/verify-email",
        headers=csrf_headers(client),
        json={"email": "expire@example.com", "code": fresh},
    )
    assert ok.status_code == 200
    reused = client.post(
        "/api/v1/auth/verify-email",
        headers=csrf_headers(client),
        json={"email": "expire@example.com", "code": fresh},
    )
    assert reused.status_code == 400


def test_login_sets_session_and_logout_revokes_it(client, application):
    signup_and_verify(client, application, "session@example.com")
    signed_in = login(
        client, kind="customer", identifier="session@example.com", password="Solarops123"
    )
    assert signed_in.status_code == 200
    assert signed_in.json()["user"]["role"] == "customer"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "session@example.com"
    logged_out = client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert logged_out.status_code == 204
    again = client.get("/api/v1/auth/me")
    assert again.status_code == 401
    assert again.json()["error"]["code"] == "unauthenticated"


def test_incorrect_credentials_do_not_authenticate(client, application):
    signup_and_verify(client, application, "auth@example.com")
    bad = login(client, kind="customer", identifier="auth@example.com", password="Solarops999")
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "invalid_credentials"
    missing = login(
        client, kind="customer", identifier="nobody@example.com", password="Solarops123"
    )
    assert missing.status_code == 401


def test_intended_role_does_not_grant_admin(client, application):
    signup_and_verify(client, application, "hint@example.com")
    signed_in = login(
        client,
        kind="customer",
        identifier="hint@example.com",
        password="Solarops123",
        intended_role="admin",
    )
    assert signed_in.status_code == 200
    assert signed_in.json()["user"]["role"] == "customer"
    staff = client.get("/api/v1/admin/employees")
    assert staff.status_code == 403
    assert staff.json()["error"]["code"] == "forbidden"


def test_missing_csrf_rejected(client, application):
    signup_and_verify(client, application, "csrf@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={
            "account_kind": "customer",
            "identifier": "csrf@example.com",
            "password": "Solarops123",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_dev_mailbox_hidden_in_test_env(client):
    response = client.get("/api/v1/dev/mailbox/person@example.com")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
