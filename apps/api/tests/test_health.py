import pytest
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

pytestmark = pytest.mark.database


def test_health_does_not_require_a_database_session_cookie(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_checks_database(client):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "up"


def test_ready_reports_database_outage():
    settings = Settings(
        app_env="test",
        database_url="postgresql+psycopg://solarops:solarops@127.0.0.1:5999/solarops_test",
        secret_key="test-secret-key-not-for-production-use!!",
        cookie_secure=False,
        trusted_origins="http://127.0.0.1:3000",
    )
    # psycopg connect timeout is passed through the URL.
    settings.database_url = settings.database_url + "?connect_timeout=2"
    outage = create_app(settings)
    with TestClient(outage) as client:
        response = client.get("/api/v1/ready")
    outage.state.engine.dispose()
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"


def test_expected_phase1_tables_exist(application):
    with application.state.engine.connect() as connection:
        rows = connection.exec_driver_sql(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).scalars()
        names = set(rows)
    expected = {
        "roles",
        "users",
        "customer_profiles",
        "employee_profiles",
        "sessions",
        "email_verification_challenges",
        "customer_sites",
        "enquiries",
        "enquiry_status_history",
        "enquiry_counters",
        "solar_packages",
        "audit_events",
        "alembic_version",
    }
    assert expected <= names


def test_no_live_weather_or_payment_provider():
    from app.services.future_boundaries import registered_providers

    assert registered_providers() == {}
