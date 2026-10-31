"""Pytest fixtures.

Tests refuse to start unless the database name is exactly solarops_test.
The session fixture drops that database's public schema and applies Alembic
from empty. Each test then truncates account and enquiry rows.
"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

TEST_DATABASE_URL = os.environ.get(
    "SOLAROPS_TEST_DATABASE_URL",
    dotenv_values(Path(__file__).resolve().parents[3] / ".env").get("SOLAROPS_TEST_DATABASE_URL")
    or "postgresql+psycopg://solarops:solarops@127.0.0.1:5432/solarops_test",
)
os.environ["SOLAROPS_APP_ENV"] = "test"
os.environ["SOLAROPS_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SOLAROPS_SECRET_KEY"] = "test-secret-key-not-for-production-use!!"
os.environ["SOLAROPS_COOKIE_SECURE"] = "false"
os.environ["SOLAROPS_LOGIN_IP_LIMIT"] = "100"
os.environ["SOLAROPS_LOGIN_IDENTIFIER_LIMIT"] = "100"
os.environ["SOLAROPS_TRUSTED_ORIGINS"] = "http://127.0.0.1:3000,http://localhost:3000"

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

get_settings.cache_clear()


def _assert_safe(url: str) -> None:
    name = make_url(url).database
    if name != "solarops_test":
        raise RuntimeError(f"Refusing to run tests against database {name!r}.")


_assert_safe(TEST_DATABASE_URL)


def _migrate() -> None:
    _assert_safe(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO CURRENT_USER"))
    engine.dispose()
    config = Config("alembic.ini")
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def application():
    _migrate()
    app = create_app(get_settings())
    yield app
    app.state.engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(request) -> Generator[None, None, None]:
    if request.node.get_closest_marker("database") is None:
        yield
        return
    application = request.getfixturevalue("application")
    application.state.limiter.reset()
    sender = application.state.email_sender
    if hasattr(sender, "messages"):
        sender.messages.clear()
    engine = application.state.engine
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE audit_events, enquiry_status_history, enquiries, "
                "customer_sites, email_verification_challenges, sessions, "
                "employee_profiles, customer_profiles, users, enquiry_counters "
                "RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest.fixture
def client(application) -> Generator[TestClient, None, None]:
    with TestClient(application) as test_client:
        yield test_client


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200, response.text
    token = response.json()["csrf_token"]
    return {"X-CSRF-Token": token}


def signup_and_verify(client: TestClient, application, email: str = "customer@example.com") -> None:
    headers = csrf_headers(client)
    created = client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Leela Nair",
            "email": email,
            "phone": "9845099999",
            "password": "Solarops123",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    code = application.state.email_sender.messages[-1].code
    verified = client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": code},
        headers=csrf_headers(client),
    )
    if verified.status_code != 200:
        # Diagnose intermittent verification failures without printing the OTP,
        # hashes, password, cookie or server secret.
        from app.core.security import secrets_match, utcnow
        from app.models.identity import EmailVerificationChallenge, User
        from sqlalchemy.orm import Session

        with Session(application.state.engine) as db:
            user = db.query(User).filter_by(email=email).one_or_none()
            challenge = (
                db.query(EmailVerificationChallenge).filter_by(user_id=user.id).first()
                if user
                else None
            )
            state = {"challenge_present": challenge is not None}
            if challenge is not None:
                state.update(
                    expired=challenge.expires_at <= utcnow(),
                    consumed=challenge.consumed_at is not None,
                    captured_code_matches=secrets_match(
                        challenge.code_hash, code, application.state.settings.secret_key
                    ),
                )
        pytest.fail(
            f"Verification HTTP {verified.status_code}; safe challenge diagnostics: {state}"
        )
    assert verified.status_code == 200, verified.text


def login(
    client: TestClient,
    *,
    kind: str,
    identifier: str,
    password: str,
    intended_role: str | None = None,
):
    body = {"account_kind": kind, "identifier": identifier, "password": password}
    if intended_role is not None:
        body["intended_role"] = intended_role
    return client.post("/api/v1/auth/login", json=body, headers=csrf_headers(client))
