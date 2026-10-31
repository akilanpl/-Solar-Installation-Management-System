"""Phase 4D release contracts: single migration head and published routes."""

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_phase4d_migration_is_single_head():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert list(script.get_heads()) == ["4d1a2b3c4d50"]


def test_intelligence_routes_in_openapi(client):
    spec = client.get("/openapi.json")
    assert spec.status_code == 200, spec.text
    paths = spec.json()["paths"]
    for path in (
        "/api/v1/customer-snapshots/{customer_id}",
        "/api/v1/customer-snapshots/{customer_id}/refresh",
        "/api/v1/cache/invalidate",
        "/api/v1/cache/metrics",
        "/api/v1/ai-assists",
        "/api/v1/ai-assists/{session_id}/confirm",
        "/api/v1/weather/sites/{site_id}/geolocation",
        "/api/v1/weather/forecasts",
        "/api/v1/weather/advisories",
        "/api/v1/weather/advisories/{advisory_id}/ack",
        "/api/v1/generation/estimates",
        "/api/v1/generation/summary",
        "/api/v1/generation/readings",
    ):
        assert path in paths, path
