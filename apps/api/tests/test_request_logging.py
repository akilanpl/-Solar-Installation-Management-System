"""Operational logs carry a usable trace while excluding sensitive request data."""

import io
import json
import logging

import pytest
from app.core.logging import RequestLogFormatter, application_logger
from app.db.session import get_db

pytestmark = pytest.mark.database


@pytest.fixture
def structured_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(RequestLogFormatter())
    logger = application_logger()
    logger.addHandler(handler)
    try:
        yield lambda: [json.loads(line) for line in stream.getvalue().splitlines()]
    finally:
        logger.removeHandler(handler)


def test_health_request_emits_actual_structured_correlation_without_query_secrets(
    client, structured_logs
):
    response = client.get("/api/v1/health?api_key=DO-NOT-LOG-THIS-FIXTURE")
    assert response.status_code == 200
    trace = response.headers["X-Request-ID"]
    matching = [row for row in structured_logs() if row.get("request_id") == trace]
    assert len(matching) == 1
    assert matching[0]["path"] == "/api/v1/health"
    assert matching[0]["method"] == "GET" and matching[0]["status"] == 200
    assert matching[0]["duration_ms"] >= 0
    assert "DO-NOT-LOG-THIS-FIXTURE" not in json.dumps(matching)


def test_failed_dependency_returns_traceable_sanitized_error(client, application, structured_logs):
    def failure():
        raise RuntimeError("DO-NOT-LOG-CREDENTIAL-FIXTURE")

    application.dependency_overrides[get_db] = failure
    try:
        response = client.get("/api/v1/ready")
    finally:
        application.dependency_overrides.pop(get_db)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    matching = [
        row
        for row in structured_logs()
        if row.get("request_id") == response.headers["X-Request-ID"]
    ]
    assert len(matching) == 1
    assert matching[0]["error_type"] == "RuntimeError" and matching[0]["status"] == 500
    assert "DO-NOT-LOG-CREDENTIAL-FIXTURE" not in response.text + json.dumps(matching)
    assert client.get("/api/v1/ready").status_code == 200


def test_formatter_is_allowlisted_and_logger_setup_is_idempotent():
    logger = application_logger()
    count = len(logger.handlers)
    assert application_logger() is logger and len(logger.handlers) == count
    record = logging.LogRecord(
        "solarops", logging.INFO, "ignored", 1, "request_completed", (), None
    )
    record.request_id = "trace-fixture"
    record.password = "DO-NOT-SERIALIZE"
    data = json.loads(RequestLogFormatter().format(record))
    assert data == {"event": "request_completed", "level": "INFO", "request_id": "trace-fixture"}
