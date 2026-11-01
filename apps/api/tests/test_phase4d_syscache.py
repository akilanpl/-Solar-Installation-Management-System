"""Phase 4D SysCache: snapshots, isolation, invalidation, concurrency, fallback.

All tests run against PostgreSQL through the real API on genuine
Phase 3 order pipelines. No performance figures are invented: the
benchmark module records measured latencies separately.
"""

import threading
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.conftest import csrf_headers, login
from tests.test_phase4a_support import (
    _all_staff,
    _create_ticket,
    _installed_order,
    _sales,
    _support,
)

pytestmark = pytest.mark.database

@pytest.fixture(autouse=True)
def _clean_phase4d_tables(application):
    """Isolated slate for Phase 4D tables.

    The shared truncate covers core tables only; Phase 4D counters and
    consumer cursors would otherwise leak between tests (e.g. a
    sequence reset makes a persisted cursor overshoot new events).
    """
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


def _schedule_slot(client, application, order_id: str) -> None:
    """Require the genuine completed installation already established by the fixture."""

    sales = _sales(client)
    jobs = client.get("/api/v1/jobs", headers=sales)
    assert jobs.status_code == 200, jobs.text
    job = next(row for row in jobs.json() if row["order_id"] == order_id)
    assert job["status"] == "completed"
    assert job["slot_starts_at"] and job["arrival_at"] and job["completed_at"]


def _installed(client, application, email="leela@example.com", serial="SN-INV-0001"):
    order, _serial = _installed_order(client, application, email, serial)
    _schedule_slot(client, application, order["id"])
    with Session(application.state.engine) as db:
        from app.models.workflow import SalesOrder

        row = db.get(SalesOrder, uuid.UUID(order["id"]))
        assert row is not None
        customer_id = str(row.customer_user_id)
    return order, customer_id


def _get_snapshot(client, headers, customer_id, scope="support-overview"):
    response = client.get(f"/api/v1/customer-snapshots/{customer_id}?scope={scope}",
                          headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_snapshot_content_and_no_secrets(client, application):
    _all_staff(application)
    order, customer_id = _installed(client, application)
    headers = _support(client)
    body = _get_snapshot(client, headers, customer_id)
    assert body["source"] in ("cache-rebuilt", "cache")
    assert body["stale"] is False
    assert body["schema_version"] == 1
    snapshot = body["snapshot"]
    assert snapshot["customer"]["full_name"] == "Leela Nair"
    assert snapshot["orders"] and snapshot["orders"][0]["reference"] == order["reference"]
    assert snapshot["equipment"], "installed serial must appear"
    assert snapshot["warranty"] and snapshot["warranty"][0]["status"] == "active"
    assert snapshot["installations"], "installation job must appear"
    assert snapshot["sites"], "customer site must appear"
    blob = __import__("json").dumps(snapshot).lower()
    for forbidden in ("password_hash", "token_hash", "otp", "session", "secret"):
        assert forbidden not in blob


def test_second_read_is_warm_cache_hit(client, application):
    _all_staff(application)
    _order, customer_id = _installed(client, application)
    headers = _support(client)
    first = _get_snapshot(client, headers, customer_id)
    assert first["source"] == "cache-rebuilt"
    second = _get_snapshot(client, headers, customer_id)
    assert second["source"] == "cache"
    assert second["business_version"] == first["business_version"]
    metrics = client.get("/api/v1/cache/metrics", headers=_support(client))
    assert metrics.status_code == 200, metrics.text
    assert metrics.json()["hits"] >= 1


def test_customer_reads_own_but_not_other(client, application):
    _all_staff(application)
    _order, customer_id = _installed(client, application)
    other_order, other_id = _installed(client, application, "arjun@example.com", "SN-INV-0002")
    assert other_order["id"] != _order["id"]
    own = _login_customer(client)
    body = _get_snapshot(client, own, customer_id)
    assert body["snapshot"]["customer"]["user_id"] == customer_id
    denied = client.get(f"/api/v1/customer-snapshots/{other_id}", headers=own)
    assert denied.status_code == 403, denied.text


def test_unknown_scope_rejected(client, application):
    _all_staff(application)
    _order, customer_id = _installed(client, application)
    headers = _support(client)
    response = client.get(f"/api/v1/customer-snapshots/{customer_id}?scope=finance",
                          headers=headers)
    assert response.status_code == 400, response.text


def test_invalidation_flow_refreshes_ticket_list(client, application):
    _all_staff(application)
    order, customer_id = _installed(client, application)
    support = _support(client)
    before = _get_snapshot(client, support, customer_id)
    assert before["snapshot"]["tickets"]["total_count"] == 0
    customer = _login_customer(client)
    _create_ticket(client, customer, order["id"])
    emitted = client.post(
        "/api/v1/cache/invalidate",
        json={"event_id": uuid.uuid4().hex, "aggregate_kind": "ticket",
              "aggregate_id": "t-1", "customer_user_id": customer_id},
        headers=_support(client),
    )
    assert emitted.status_code == 200, emitted.text
    assert emitted.json()["snapshots_invalidated"] == 1
    after = _get_snapshot(client, _support(client), customer_id)
    assert after["snapshot"]["tickets"]["total_count"] == 1
    assert after["business_version"] != before["business_version"]


def test_invalidate_is_idempotent(client, application):
    _all_staff(application)
    _order, customer_id = _installed(client, application)
    support = _support(client)
    _get_snapshot(client, support, customer_id)
    event_id = uuid.uuid4().hex
    payload = {"event_id": event_id, "aggregate_kind": "finance",
               "aggregate_id": "pay-1", "customer_user_id": customer_id}
    first = client.post("/api/v1/cache/invalidate", json=payload, headers=_support(client))
    assert first.status_code == 200, first.text
    second = client.post("/api/v1/cache/invalidate", json=payload, headers=_support(client))
    assert second.status_code == 200, second.text
    assert second.json()["snapshots_invalidated"] == 0


def test_out_of_order_event_does_not_invalidate(client, application):
    _all_staff(application)
    _order, customer_id = _installed(client, application)
    support = _support(client)
    fresh = _get_snapshot(client, support, customer_id)
    assert fresh["stale"] is False
    old_event = client.post(
        "/api/v1/cache/invalidate",
        json={"event_id": uuid.uuid4().hex, "aggregate_kind": "ticket",
              "aggregate_id": "t-old", "customer_user_id": customer_id,
              "occurred_at": "2020-01-01T00:00:00Z"},
        headers=_support(client),
    )
    assert old_event.status_code == 200, old_event.text
    assert old_event.json()["out_of_order_skipped"] >= 1
    current = _get_snapshot(client, _support(client), customer_id)
    assert current["source"] == "cache"
    assert current["stale"] is False


def test_concurrent_refresh_single_row(client, application):
    _all_staff(application)
    _order, customer_id = _installed(client, application)
    headers = _support(client)
    outcomes: list = []

    def _refresh():
        response = client.post(f"/api/v1/customer-snapshots/{customer_id}/refresh",
                               headers=headers)
        outcomes.append(response.status_code)

    threads = [threading.Thread(target=_refresh) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes and all(code == 200 for code in outcomes), outcomes
    with Session(application.state.engine) as db:
        from app.models.phase4d import CustomerSnapshotCache

        rows = db.scalars(
            select(CustomerSnapshotCache).where(
                CustomerSnapshotCache.customer_user_id == uuid.UUID(customer_id))
        ).all()
        assert len(rows) == 1


def test_forced_fallback_serves_postgresql(client, application, monkeypatch):
    _all_staff(application)
    _order, customer_id = _installed(client, application)
    support = _support(client)
    _get_snapshot(client, support, customer_id)
    monkeypatch.setattr(application.state.settings, "syscache_force_fallback", True)
    try:
        body = _get_snapshot(client, _support(client), customer_id)
    finally:
        monkeypatch.setattr(application.state.settings, "syscache_force_fallback", False)
    assert body["source"] == "postgresql-fallback"
    assert body["snapshot"]["orders"], "fallback must serve real PostgreSQL data"


def test_schema_rollover_rebuilds(client, application):
    _all_staff(application)
    _order, customer_id = _installed(client, application)
    support = _support(client)
    _get_snapshot(client, support, customer_id)
    with Session(application.state.engine) as db:
        from app.models.phase4d import CustomerSnapshotCache

        row = db.scalar(
            select(CustomerSnapshotCache).where(
                CustomerSnapshotCache.customer_user_id == uuid.UUID(customer_id))
        )
        assert row is not None
        row.schema_version = 0
        db.commit()
    body = _get_snapshot(client, _support(client), customer_id)
    assert body["schema_version"] == 1
    assert body["source"] == "cache-rebuilt"


def test_technician_cannot_read_snapshot(client, application):
    _all_staff(application)
    from tests.test_phase4a_support import _technician

    _order, customer_id = _installed(client, application)
    tech = _technician(client)
    response = client.get(f"/api/v1/customer-snapshots/{customer_id}", headers=tech)
    assert response.status_code == 403, response.text
    assert csrf_headers(client) is not None
