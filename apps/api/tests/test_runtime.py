"""Real ASGI boundary checks that never require a running database."""

import json
from pathlib import Path

import pytest
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tests.conftest import _assert_safe, csrf_headers


@pytest.fixture
def runtime_client():
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://solarops:solarops@127.0.0.1:5999/solarops_test?connect_timeout=2",
        secret_key="isolated-runtime-test-secret-key-32-characters",
        cookie_secure=False,
        smtp_host=None,
    )
    application = create_app(settings)
    try:
        with TestClient(application, raise_server_exceptions=False) as client:
            yield client
    finally:
        application.state.engine.dispose()


def test_liveness_and_docs_without_database(runtime_client):
    assert runtime_client.get("/api/v1/health").json() == {"status": "ok"}
    assert runtime_client.get("/docs").status_code == 200
    response = runtime_client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/enquiries" in response.json()["paths"]


def test_openapi_matches_checked_in_contract(runtime_client):
    contract = Path(__file__).resolve().parents[3] / "contracts/generated/openapi.json"
    assert runtime_client.get("/openapi.json").json() == json.loads(
        contract.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "path",
    ["/api/v1/auth/me", "/api/v1/enquiries", "/api/v1/admin/employees"],
)
def test_anonymous_reads_rejected_without_database(runtime_client, path):
    response = runtime_client.get(path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


@pytest.mark.parametrize("mode", ["missing", "mismatch", "untrusted_origin"])
def test_csrf_boundary_precedes_database_access(runtime_client, mode):
    headers = {} if mode == "missing" else csrf_headers(runtime_client)
    if mode == "mismatch":
        headers["X-CSRF-Token"] = "wrong-token"
    if mode == "untrusted_origin":
        headers["Origin"] = "https://untrusted.example"
    response = runtime_client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "invalid", "full_name": "Leela", "phone": "9845099999", "password": "short"},
        {
            "email": "valid@example.com",
            "full_name": "Leela",
            "phone": "9845099999",
            "password": "Solarops123",
            "role": "admin",
        },
    ],
    ids=["missing-fields", "invalid-values", "role-mass-assignment"],
)
def test_invalid_signup_never_reaches_database(runtime_client, payload):
    response = runtime_client.post(
        "/api/v1/auth/signup", json=payload, headers=csrf_headers(runtime_client)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "Solarops123" not in response.text


def test_readiness_reports_real_connection_failure(runtime_client):
    response = runtime_client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "The database is not available.",
            "details": [],
        }
    }


def test_unexpected_exception_returns_safe_error(runtime_client):
    @runtime_client.app.get("/qa-only-failure")
    def fail():
        raise RuntimeError("private-internal-marker")

    response = runtime_client.get("/qa-only-failure")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private-internal-marker" not in response.text
    assert "Traceback" not in response.text


def test_mailbox_hidden_in_test(runtime_client):
    assert runtime_client.get("/api/v1/dev/mailbox/person@example.com").status_code == 404


@pytest.mark.parametrize(
    "method,path,status",
    [
        ("get", "/api/v1/not-a-route", 404),
        ("delete", "/api/v1/health", 405),
    ],
)
def test_unknown_route_and_unsupported_method(runtime_client, method, path, status):
    assert runtime_client.request(method, path).status_code == status


def test_missing_required_configuration_is_controlled(monkeypatch):
    monkeypatch.delenv("SOLAROPS_DATABASE_URL", raising=False)
    monkeypatch.delenv("SOLAROPS_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)
    assert {item["loc"] for item in error.value.errors()} >= {("database_url",), ("secret_key",)}


@pytest.mark.parametrize("name", ["solarops", "production", "solarops_test_copy"])
def test_database_guard_rejects_non_test_names(name):
    with pytest.raises(RuntimeError, match="Refusing to run tests"):
        _assert_safe(f"postgresql+psycopg://localhost/{name}")
