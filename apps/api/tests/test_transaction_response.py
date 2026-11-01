"""Success and session cookies cannot escape before durable transaction commit."""

import pytest
from app.models.identity import Session as AuthSession
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.test_phase3_warehouse_installation import _all_staff

pytestmark = pytest.mark.database


def test_login_session_is_committed_when_response_headers_are_sent(application):
    _all_staff(application)
    counts = []

    async def observed(scope, receive, send):
        async def observe(message):
            if (
                scope["type"] == "http"
                and scope["path"] == "/api/v1/auth/login"
                and message["type"] == "http.response.start"
                and message["status"] == 200
            ):
                with Session(application.state.engine) as db:
                    counts.append(db.scalar(select(func.count()).select_from(AuthSession)))
            await send(message)

        await application(scope, receive, observe)

    with TestClient(observed) as client:
        token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={
                "account_kind": "employee",
                "identifier": "EMP-WH-901",
                "password": "Staffpass123",
            },
            headers={"X-CSRF-Token": token},
        )
        # The test fixture uses EMP-WH-901; never inspect or output cookie contents.
        assert response.status_code == 200, response.text
    assert counts == [1], (
        "Session must already be visible from an independent connection at response start"
    )


def test_failed_commit_cannot_emit_success_or_usable_session_cookie(application):
    _all_staff(application)
    original = application.state.session_factory

    class RefuseCommit(Session):
        def commit(self):
            raise RuntimeError("Controlled test commit failure")

    application.state.session_factory = sessionmaker(
        bind=application.state.engine,
        class_=RefuseCommit,
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        with TestClient(application, raise_server_exceptions=False) as client:
            token = client.get("/api/v1/auth/csrf").json()["csrf_token"]
            result = client.post(
                "/api/v1/auth/login",
                json={
                    "account_kind": "employee",
                    "identifier": "EMP-WH-901",
                    "password": "Staffpass123",
                },
                headers={"X-CSRF-Token": token},
            )
            assert result.status_code == 500
            assert "solarops_session" not in result.cookies
    finally:
        application.state.session_factory = original
    with original() as db:
        assert db.scalar(select(func.count()).select_from(AuthSession)) == 0


def test_mfa_enrollment_is_durable_before_success_headers(application):
    from app.models.phase4e import MfaFactor
    from tests.test_phase4a_support import _technician

    _all_staff(application)
    visible_factors = []

    async def observed(scope, receive, send):
        async def observe(message):
            if (scope["type"] == "http"
                    and scope["path"] == "/api/v1/auth/mfa/totp/enroll/start"
                    and message["type"] == "http.response.start"
                    and message["status"] == 200):
                with Session(application.state.engine) as db:
                    visible_factors.append(db.scalar(select(func.count()).select_from(MfaFactor)))
            await send(message)
        await application(scope, receive, observe)

    with TestClient(observed) as client:
        headers = _technician(client)
        result = client.post("/api/v1/auth/mfa/totp/enroll/start",
                             json={"password": "Staffpass123", "label": "Durable enrollment"},
                             headers=headers)
        assert result.status_code == 200
        assert result.json()["factor_id"]
    assert visible_factors == [1], "MFA enrollment must commit before response headers"


def test_pool_rollback_keeps_utc_session_timezone():
    from app.db.session import build_engine
    from sqlalchemy import text
    from tests.conftest import TEST_DATABASE_URL

    engine = build_engine(TEST_DATABASE_URL)
    try:
        for _ in range(3):
            with engine.connect() as connection:
                assert connection.scalar(text("SHOW TIME ZONE")) == "UTC"
                connection.execute(text("SELECT 1"))
                connection.rollback()
                assert connection.scalar(text("SHOW TIME ZONE")) == "UTC"
    finally:
        engine.dispose()
