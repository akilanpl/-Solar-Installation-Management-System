"""Transaction rollback and session timezones cannot change signed summaries."""

import hashlib
import json
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from app.core.security import hash_secret
from app.db.session import build_engine
from app.models.identity import User
from app.models.phase3 import InstallationJob
from app.services.installation_service import _accepted_summary_matches, work_summary
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from tests.conftest import TEST_DATABASE_URL, _assert_safe
from tests.test_installation_hardening import prepared
from tests.test_phase3_warehouse_installation import _login, _technician

pytestmark = pytest.mark.database


def test_new_connection_utc_setting_survives_transaction_rollback():
    _assert_safe(TEST_DATABASE_URL)
    url = make_url(TEST_DATABASE_URL).update_query_dict({"options": "-c timezone=Asia/Kolkata"})
    engine = build_engine(url)
    try:
        # Reuse one pooled connection. An uncommitted SET is otherwise undone
        # by closing the first read-only connection or rolling back a request.
        for _ in range(3):
            with engine.connect() as db:
                assert db.scalar(text("SHOW TIME ZONE")) == "UTC"
                db.rollback()
                assert db.scalar(text("SHOW TIME ZONE")) == "UTC"
    finally:
        engine.dispose()


def test_identical_work_summary_has_identical_hash_across_session_timezones(client, application):
    job, _, _, _ = prepared(client, application)
    reviewer = User(id=uuid.uuid4(), role_code="admin")
    summaries = []
    for zone in ("UTC", "Asia/Kolkata", "America/New_York"):
        with Session(application.state.engine) as db:
            db.execute(text("SELECT set_config('TimeZone', :zone, true)"), {"zone": zone})
            summaries.append(work_summary(db, reviewer, uuid.UUID(job["id"])))
            db.rollback()
    assert len({row["summary_hash"] for row in summaries}) == 1
    assert all(row["summary"]["arrival_at"].endswith("+00:00") for row in summaries)


@pytest.mark.parametrize(
    "signed",
    [
        None,
        {},
        {"arrival_at": None},
        {"arrival_at": "invalid"},
        {"arrival_at": "2026-01-01T12:00:00"},
        {"arrival_at": "2026-01-01T12:00:00+00:00", "evidence": "changed"},
    ],
)
def test_legacy_summary_normalization_does_not_accept_missing_or_changed_work(signed):
    current = {
        "summary_hash": "current-hash",
        "summary": {"arrival_at": "2026-01-01T12:00:00+00:00", "evidence": "original"},
    }
    assert (
        _accepted_summary_matches({"summary_hash": "old-hash", "summary": signed}, current) is False
    )


def test_legacy_signed_timezone_is_preserved_when_completing_job(client, application):
    job, code, _, _ = prepared(client, application)
    customer = _login(client, "customer", "leela@example.com", "Solarops123")
    path = f"/api/v1/jobs/{job['id']}"
    summary = client.get(f"{path}/work-summary").json()
    signed = client.post(
        f"{path}/signature",
        headers=customer,
        json={
            "signature_ref": "Leela Nair",
            "customer_confirmed": True,
            "summary_hash": summary["summary_hash"],
        },
    )
    assert signed.status_code == 200, signed.text
    legacy = deepcopy(signed.json()["signature"])
    instant = datetime.fromisoformat(legacy["summary"]["arrival_at"])
    legacy["summary"]["arrival_at"] = instant.astimezone(
        timezone(timedelta(hours=5, minutes=30))
    ).isoformat()
    legacy["summary_hash"] = hashlib.sha256(
        json.dumps(legacy["summary"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    legacy.pop("payload_hmac")
    legacy["payload_hmac"] = hash_secret(
        json.dumps(legacy, sort_keys=True, separators=(",", ":")),
        application.state.settings.secret_key,
    )
    # Fixture reproduces a valid pre-fix signed record. Application code must
    # verify its original HMAC and retain the original acceptance byte values.
    with Session(application.state.engine) as db:
        db.get(InstallationJob, uuid.UUID(job["id"])).signature = legacy
        db.commit()
    tech = _technician(client)
    assert client.post(f"{path}/customer-otp", headers=tech, json={"code": code}).status_code == 200
    completed = client.post(f"{path}/completion", headers=tech)
    assert completed.status_code == 200, completed.text
    assert completed.json()["signature"] == legacy
