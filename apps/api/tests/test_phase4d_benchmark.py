"""Phase 4D SysCache benchmark: real measurements, reproducible workload.

Measures indexed PostgreSQL build latency, cold-cache latency, warm
cache latency, hit/miss rates, p50/p95, concurrent behavior and
failure recovery. Results are printed and written to
/tmp/phase4d_benchmark.json (not committed). No figures are invented:
every number below comes from a timed run in this test.
"""

import json
import statistics
import threading
import time
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session
from tests.test_phase4a_support import _all_staff, _installed_order, _support

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


WARM_REQUESTS = 50
CONCURRENT_THREADS = 10
REPORT_PATH = "/tmp/phase4d_benchmark.json"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(pct / 100.0 * len(ordered)))
    return ordered[index]


def _stats(label: str, values: list[float]) -> dict:
    return {
        "label": label,
        "n": len(values),
        "p50_ms": round(_percentile(values, 50), 2),
        "p95_ms": round(_percentile(values, 95), 2),
        "mean_ms": round(statistics.fmean(values), 2),
        "min_ms": round(min(values), 2),
        "max_ms": round(max(values), 2),
    }


def test_syscache_benchmark_and_recovery(client, application, monkeypatch):
    _all_staff(application)
    order, _serial = _installed_order(client, application)
    with Session(application.state.engine) as db:
        from app.models.workflow import SalesOrder

        customer_id = str(db.get(SalesOrder, uuid.UUID(order["id"])).customer_user_id)
    headers = _support(client)
    url = f"/api/v1/customer-snapshots/{customer_id}"

    with Session(application.state.engine) as db:
        from app.models.phase4d import CustomerSnapshotCache

        db.execute(delete(CustomerSnapshotCache))
        db.commit()

    cold: list[float] = []
    for _ in range(5):
        with Session(application.state.engine) as db:
            from app.models.phase4d import CustomerSnapshotCache

            db.execute(delete(CustomerSnapshotCache))
            db.commit()
        started = time.perf_counter()
        response = client.get(url, headers=headers)
        cold.append((time.perf_counter() - started) * 1000.0)
        assert response.status_code == 200, response.text
        assert response.json()["source"] == "cache-rebuilt"
    cold_version = client.get(url, headers=headers).json()["business_version"]

    warm: list[float] = []
    for _ in range(WARM_REQUESTS):
        started = time.perf_counter()
        response = client.get(url, headers=headers)
        warm.append((time.perf_counter() - started) * 1000.0)
        assert response.status_code == 200, response.text
        assert response.json()["source"] == "cache"
        assert response.json()["business_version"] == cold_version

    outcomes: list[int] = []
    versions: list[str] = []

    def _hit():
        response = client.get(url, headers=headers)
        outcomes.append(response.status_code)
        if response.status_code == 200:
            versions.append(response.json()["business_version"])

    threads = [threading.Thread(target=_hit) for _ in range(CONCURRENT_THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert all(code == 200 for code in outcomes), outcomes
    assert set(versions) == {cold_version}

    monkeypatch.setattr(application.state.settings, "syscache_force_fallback", True)
    try:
        started = time.perf_counter()
        fallback = client.get(url, headers=headers)
        fallback_ms = (time.perf_counter() - started) * 1000.0
    finally:
        monkeypatch.setattr(application.state.settings, "syscache_force_fallback", False)
    assert fallback.status_code == 200, fallback.text
    assert fallback.json()["source"] == "postgresql-fallback"

    metrics = client.get("/api/v1/cache/metrics", headers=_support(client)).json()
    total_hits = metrics["hits"]
    report = {
        "workload": {
            "warm_requests": WARM_REQUESTS,
            "cold_rebuilds": 5,
            "concurrent_threads": CONCURRENT_THREADS,
        },
        "cold_cache_rebuild": _stats("cold GET (build + store)", cold),
        "warm_cache_hit": _stats("warm GET (cache)", warm),
        "postgresql_fallback_single_ms": round(fallback_ms, 2),
        "hit_rate_warm_phase": 1.0,
        "concurrent_success_rate": sum(1 for c in outcomes if c == 200) / len(outcomes),
        "server_metrics": metrics,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("\nSYSCACHE BENCHMARK:\n" + json.dumps(report, indent=2))
    assert total_hits >= WARM_REQUESTS
    assert metrics["fallbacks"] >= 1
    assert metrics["rebuilds"] >= 5
