"""Actual shared counters and controlled connection failure, no shared server stop."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.core.errors import AppError
from app.core.rate_limit import SharedRateLimiter
from app.core.security import hash_secret
from app.db.session import build_session_factory
from app.models.rate_limit import RateLimitBucket
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.database


def test_two_worker_instances_share_limit_and_survive_recreation(application):
    key = "isolated-rate-" + uuid.uuid4().hex
    first = SharedRateLimiter(application.state.engine, "isolated-test-pepper")
    second = SharedRateLimiter(application.state.engine, "isolated-test-pepper")
    first.check(key, 2, 60)
    second.check(key, 2, 60)
    with pytest.raises(AppError) as exc:
        SharedRateLimiter(application.state.engine, "isolated-test-pepper").check(key, 2, 60)
    assert exc.value.status_code == 429
    with Session(application.state.engine) as db:
        row = db.get(RateLimitBucket, hash_secret(key, "isolated-test-pepper"))
        assert row.hits == 3
        assert key not in row.key_hash
        db.execute(
            text(
                "UPDATE rate_limit_buckets SET expires_at=clock_timestamp()-interval '1 second' WHERE key_hash=:key"
            ),
            {"key": row.key_hash},
        )
        db.commit()
    first.check(key, 2, 60)
    with Session(application.state.engine) as db:
        assert db.get(RateLimitBucket, hash_secret(key, "isolated-test-pepper")).hits == 1


def test_concurrent_workers_accept_only_configured_number(application):
    key = "isolated-concurrent-" + uuid.uuid4().hex

    def call(_):
        try:
            SharedRateLimiter(application.state.engine, "isolated-pepper").check(key, 5, 60)
            return "allowed"
        except AppError as exc:
            assert exc.status_code == 429
            return "limited"

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(call, range(12)))
    assert outcomes.count("allowed") == 5
    assert outcomes.count("limited") == 7


def test_database_connection_outage_returns_503_then_recovers(client, application):
    assert client.get("/api/v1/ready").status_code == 200
    good_engine = application.state.engine
    good_factory = application.state.session_factory
    bad_engine = create_engine(
        "postgresql+psycopg://127.0.0.1:65431/solarops_release_test_20261031",
        connect_args={"connect_timeout": 1},
    )
    try:
        application.state.engine = bad_engine
        application.state.session_factory = build_session_factory(bad_engine)
        failed = client.get("/api/v1/ready")
        assert failed.status_code == 503, failed.text
        assert failed.json()["error"]["code"] == "database_unavailable"
    finally:
        application.state.engine = good_engine
        application.state.session_factory = good_factory
        bad_engine.dispose()
    assert client.get("/api/v1/ready").status_code == 200
