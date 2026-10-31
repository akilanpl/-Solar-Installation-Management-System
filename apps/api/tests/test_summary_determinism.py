"""The same arrival instant must hash identically across connection timezones."""

import json

import pytest
from app.services import installation_service
from sqlalchemy import text
from tests.test_phase3_warehouse_installation import (
    test_cross_phase_order_to_completed_installation as exercise,
)

pytestmark = pytest.mark.database


@pytest.mark.parametrize(
    "zones", [("Asia/Kolkata", "UTC"), ("America/New_York", "Asia/Tokyo"), ("Europe/London", "UTC")]
)
def test_review_hash_is_stable_across_authenticated_requests(
    client, application, monkeypatch, zones
):
    original = installation_service.work_summary
    reviews = []

    def observe(db, user, job_id):
        db.execute(
            text("SELECT set_config('TimeZone', :zone, true)"), {"zone": zones[len(reviews) % 2]}
        )
        result = original(db, user, job_id)
        canonical = json.dumps(result["summary"], sort_keys=True)
        if reviews:
            assert result["summary_hash"] == reviews[0][0]
            assert canonical == reviews[0][1]
        reviews.append((result["summary_hash"], canonical))
        return result

    monkeypatch.setattr(installation_service, "work_summary", observe)
    exercise(client, application)
    assert len(reviews) >= 3
