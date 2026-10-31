"""Phase 4D edge and error paths: 4xx/503 branches across intelligence routes.

Complements the happy-path suites by exercising every documented
rejection: unknown resources, cross-customer access, invalid inputs,
duplicate idempotency keys, expired drafts and provider failures.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.services import ai_assist_service, weather_service
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers, login
from tests.test_phase4a_support import (
    _all_staff,
    _create_ticket,
    _installed_order,
    _support,
    _technician,
)

pytestmark = pytest.mark.database


@pytest.fixture(autouse=True)
def _clean_phase4d_tables(application):
    from sqlalchemy import text as _text

    with application.state.engine.begin() as connection:
        connection.execute(
            _text(
                "TRUNCATE TABLE phase4d_customer_snapshots, phase4d_cache_outbox, "
                "phase4d_cache_consumers, phase4d_cache_metrics, phase4d_ai_assists, "
                "phase4d_site_geolocations, phase4d_forecast_snapshots, "
                "phase4d_weather_advisories, phase4d_generation_readings "
                "RESTART IDENTITY CASCADE"
            )
        )
    yield


def _login_customer(client, email="leela@example.com") -> dict[str, str]:
    response = login(client, kind="customer", identifier=email, password="Solarops123")
    assert response.status_code == 200, response.text
    return csrf_headers(client)


def _installed(client, application, email="leela@example.com", serial="SN-INV-0001"):
    order, _serial = _installed_order(client, application, email, serial)
    with Session(application.state.engine) as db:
        from app.models.workflow import SalesOrder

        row = db.get(SalesOrder, uuid.UUID(order["id"]))
        assert row is not None
        customer_id = str(row.customer_user_id)
        site_id = str(row.site_id)
    return order, customer_id, site_id


class _StormStub:
    name = "stub-storm"

    def fetch(self, latitude, longitude):
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        return {
            "issued_at": now.isoformat(),
            "units": "metric",
            "periods": [{"starts_at": now.isoformat(), "rain_mm_per_h": 0.0, "wind_ms": 1.0}],
        }


def _verify_site(client, headers, site_id):
    response = client.post(
        f"/api/v1/weather/sites/{site_id}/geolocation",
        json={"latitude": 17.385, "longitude": 78.4867, "verified": True},
        headers=headers,
    )
    assert response.status_code == 200, response.text


def test_assist_unknown_ticket_is_404(client, application):
    _all_staff(application)
    _installed(client, application)
    response = client.post(
        "/api/v1/ai-assists",
        json={"complaint_text": "Inverter not working.", "ticket_id": str(uuid.uuid4())},
        headers=_support(client),
    )
    assert response.status_code == 404, response.text


def test_customer_cannot_assist_other_ticket_or_identity(client, application):
    _all_staff(application)
    order, _customer_id, _site = _installed(client, application)
    _installed(client, application, "arjun@example.com", "SN-INV-0002")
    customer = _login_customer(client)
    ticket = _create_ticket(client, customer, order["id"])
    arjun = _login_customer(client, "arjun@example.com")
    denied_ticket = client.post(
        "/api/v1/ai-assists",
        json={"complaint_text": "Mine too.", "ticket_id": ticket["id"]},
        headers=arjun,
    )
    assert denied_ticket.status_code == 403, denied_ticket.text
    denied_identity = client.post(
        "/api/v1/ai-assists",
        json={"complaint_text": "Mine too.", "customer_user_id": str(uuid.uuid4())},
        headers=_login_customer(client),
    )
    assert denied_identity.status_code == 403, denied_identity.text


def test_snapshot_unknown_customer_is_404(client, application):
    _all_staff(application)
    missing_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/customer-snapshots/{missing_id}",
                          headers=_support(client))
    assert response.status_code == 404, response.text
    refresh = client.post(f"/api/v1/customer-snapshots/{missing_id}/refresh",
                          headers=_support(client))
    assert refresh.status_code == 404, refresh.text


def test_customer_cannot_refresh_or_read_metrics(client, application):
    _all_staff(application)
    _order, customer_id, _site = _installed(client, application)
    customer = _login_customer(client)
    refresh = client.post(f"/api/v1/customer-snapshots/{customer_id}/refresh", headers=customer)
    assert refresh.status_code == 403, refresh.text
    metrics = client.get("/api/v1/cache/metrics", headers=_login_customer(client))
    assert metrics.status_code == 403, metrics.text


def test_invalidate_rejects_unknown_kind(client, application):
    _all_staff(application)
    response = client.post(
        "/api/v1/cache/invalidate",
        json={"event_id": uuid.uuid4().hex, "aggregate_kind": "ledger",
              "aggregate_id": "x"},
        headers=_support(client),
    )
    assert response.status_code == 422, response.text


def test_forecast_duplicate_request_id_returns_same_row(client, application, monkeypatch):
    _all_staff(application)
    _order, _customer_id, site_id = _installed(client, application)
    monkeypatch.setattr(weather_service, "resolve_provider", lambda settings: _StormStub())
    support = _support(client)
    _verify_site(client, support, site_id)
    payload = {"site_id": site_id, "request_id": "req-duplicate-001"}
    first = client.post("/api/v1/weather/forecasts", json=payload,
                        headers=_support(client))
    assert first.status_code == 201, first.text
    second = client.post("/api/v1/weather/forecasts", json=payload,
                         headers=_support(client))
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]


def test_forecast_bad_payload_and_timeout(client, application, monkeypatch):
    _all_staff(application)
    _order, _customer_id, site_id = _installed(client, application)
    support = _support(client)
    _verify_site(client, support, site_id)

    class _BadStub:
        name = "bad"

        def fetch(self, latitude, longitude):
            return {"issued_at": "not-a-time", "units": "metric", "periods": []}

    real_resolve = weather_service.resolve_provider
    monkeypatch.setattr(weather_service, "resolve_provider", lambda settings: _BadStub())
    bad = client.post(
        "/api/v1/weather/forecasts",
        json={"site_id": site_id, "request_id": "req-bad-001"},
        headers=_support(client),
    )
    assert bad.status_code == 502, bad.text

    monkeypatch.setattr(weather_service, "resolve_provider", real_resolve)
    monkeypatch.setattr(application.state.settings, "weather_provider_url",
                        "http://127.0.0.1:1/unreachable")
    slow = client.post(
        "/api/v1/weather/forecasts",
        json={"site_id": site_id, "request_id": "req-slow-001"},
        headers=_support(client),
    )
    assert slow.status_code == 503, slow.text


def test_advisory_unknown_and_bad_action(client, application):
    _all_staff(application)
    missing = client.post(
        f"/api/v1/weather/advisories/{uuid.uuid4()}/ack",
        json={"action": "acknowledge"},
        headers=_support(client),
    )
    assert missing.status_code == 404, missing.text
    bad_action = client.post(
        f"/api/v1/weather/advisories/{uuid.uuid4()}/ack",
        json={"action": "snooze"},
        headers=_support(client),
    )
    assert bad_action.status_code == 422, bad_action.text


def test_geolocation_unknown_site_is_404(client, application):
    _all_staff(application)
    response = client.post(
        f"/api/v1/weather/sites/{uuid.uuid4()}/geolocation",
        json={"latitude": 1.0, "longitude": 2.0},
        headers=_support(client),
    )
    assert response.status_code == 404, response.text


def test_estimate_unknown_order_and_bad_interval(client, application):
    _all_staff(application)
    missing = client.get("/api/v1/generation/estimates",
                         params={"order_id": str(uuid.uuid4())},
                         headers=_support(client))
    assert missing.status_code == 404, missing.text
    _order, _customer_id, _site = _installed(client, application)
    bad_interval = client.get(
        "/api/v1/generation/estimates",
        params={"order_id": _order["id"], "interval": "fortnight"},
        headers=_support(client),
    )
    assert bad_interval.status_code == 400, bad_interval.text
    bad_status = client.get(
        "/api/v1/generation/readings",
        params={"order_id": _order["id"], "status": "maybe"},
        headers=_support(client),
    )
    assert bad_status.status_code == 400, bad_status.text


def test_estimate_unknown_capacity_is_422(client, application):
    _all_staff(application)
    order, _customer_id, _site = _installed(client, application)
    with Session(application.state.engine) as db:
        from app.models.workflow import SalesOrder

        row = db.get(SalesOrder, uuid.UUID(order["id"]))
        assert row is not None
        row.package_code = "PKG-NOPE-9"
        db.commit()
    response = client.get("/api/v1/generation/estimates",
                          params={"order_id": order["id"]},
                          headers=_support(client))
    assert response.status_code == 422, response.text


def test_cross_customer_generation_and_readings_denied(client, application):
    _all_staff(application)
    order, _customer_id, _site = _installed(client, application)
    _installed(client, application, "arjun@example.com", "SN-INV-0002")
    arjun = _login_customer(client, "arjun@example.com")
    denied_summary = client.get("/api/v1/generation/summary",
                                params={"order_id": order["id"]}, headers=arjun)
    assert denied_summary.status_code == 403, denied_summary.text
    denied_list = client.get("/api/v1/generation/readings",
                             params={"order_id": order["id"]}, headers=arjun)
    assert denied_list.status_code == 403, denied_list.text
    tech_denied = client.get("/api/v1/generation/summary",
                             params={"order_id": order["id"]},
                             headers=_technician(client))
    assert tech_denied.status_code == 403, tech_denied.text


def test_reading_blank_fields_rejected(client, application):
    _all_staff(application)
    order, _customer_id, _site = _installed(client, application)
    response = client.post(
        "/api/v1/generation/readings",
        json={"order_id": order["id"], "device_ref": "  ", "event_id": "e1",
              "source": "acme", "measured_at": datetime.now(UTC).isoformat(),
              "energy_wh": "10"},
        headers=_support(client),
    )
    assert response.status_code == 400, response.text


def test_assist_discard_and_expiry(client, application):
    _all_staff(application)
    _installed(client, application)
    created = client.post(
        "/api/v1/ai-assists",
        json={"complaint_text": "The inverter hums loudly at night."},
        headers=_support(client),
    )
    assert created.status_code == 201, created.text
    discarded = client.post(
        f"/api/v1/ai-assists/{created.json()['id']}/confirm",
        json={"decision": "discarded", "note": "Duplicate of phone intake."},
        headers=_support(client),
    )
    assert discarded.status_code == 200, discarded.text
    assert discarded.json()["status"] == "discarded"

    second = client.post(
        "/api/v1/ai-assists",
        json={"complaint_text": "Panels look dusty after the storm."},
        headers=_support(client),
    )
    assert second.status_code == 201, second.text
    with Session(application.state.engine) as db:
        from app.models.phase4d import AiAssistSession

        row = db.get(AiAssistSession, uuid.UUID(second.json()["id"]))
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()
    expired = client.post(
        f"/api/v1/ai-assists/{second.json()['id']}/confirm",
        json={"decision": "confirmed"},
        headers=_support(client),
    )
    assert expired.status_code == 410, expired.text


def test_assist_bad_decision_and_oversize_summary(client, application):
    _all_staff(application)
    _installed(client, application)
    created = client.post(
        "/api/v1/ai-assists",
        json={"complaint_text": "Battery drains by morning."},
        headers=_support(client),
    )
    assert created.status_code == 201, created.text
    bad_decision = client.post(
        f"/api/v1/ai-assists/{created.json()['id']}/confirm",
        json={"decision": "escalated"},
        headers=_support(client),
    )
    assert bad_decision.status_code == 422, bad_decision.text
    oversize = client.post(
        f"/api/v1/ai-assists/{created.json()['id']}/confirm",
        json={"decision": "confirmed", "edited_summary": "x" * 2001},
        headers=_support(client),
    )
    assert oversize.status_code == 422, oversize.text


def test_provider_malformed_and_unsafe_drafts_rejected(client, application, monkeypatch):
    _all_staff(application)
    _installed(client, application)
    monkeypatch.setattr(application.state.settings, "ai_model_url", "http://stub/model")

    class _NonDict:
        status_code = 200

        def json(self):
            return ["not", "a", "dict"]

    monkeypatch.setattr(ai_assist_service.httpx, "post", lambda *a, **k: _NonDict())
    malformed = client.post(
        "/api/v1/ai-assists",
        json={"complaint_text": "Inverter shows E-03.", "mode": "provider"},
        headers=_support(client),
    )
    assert malformed.status_code == 502, malformed.text

    class _Unsafe:
        status_code = 200

        def json(self):
            return {
                "summary": "Warranty approved automatically.",
                "symptoms": [],
                "fault_codes": [],
                "suggested_categories": ["inverter"],
                "missing_information": [],
                "recommended_priority": "low",
                "priority_reasons": ["model says so"],
                "followup_questions": [],
            }

    monkeypatch.setattr(ai_assist_service.httpx, "post", lambda *a, **k: _Unsafe())
    unsafe = client.post(
        "/api/v1/ai-assists",
        json={"complaint_text": "Inverter shows E-03.", "mode": "provider"},
        headers=_support(client),
    )
    assert unsafe.status_code == 422, unsafe.text
    assert unsafe.json()["error"]["code"] == "assist_unsafe_output"
