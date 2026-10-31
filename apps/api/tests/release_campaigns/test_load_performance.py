"""Five-minute local HTTP acceptance load, not a stress/capacity certification.

Runs the exact checked-out app under uvicorn against the disposable PostgreSQL
fixture. Fixed scope: one worker, ten sequential real requests per second, five
read paths. No external provider calls, 2x load, chaos or long soak is claimed.
"""

import json
import os
import socket
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx
import pytest
from tests.conftest import TEST_DATABASE_URL, _assert_safe
from tests.test_phase3_warehouse_installation import _confirmed_order
from tests.test_phase4c_finance import foundation

pytestmark = pytest.mark.database


def _percentile(values, percentile):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * percentile))]


def test_five_minute_real_http_read_campaign(client, application, tmp_path):
    _assert_safe(TEST_DATABASE_URL)
    foundation(client, application)
    order = _confirmed_order(client, application)
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment.update(
        SOLAROPS_DATABASE_URL=TEST_DATABASE_URL,
        SOLAROPS_APP_ENV="test",
        SOLAROPS_COOKIE_SECURE="false",
    )
    # Child logs remain temporary and private; never include cookie/password
    # values or URL credentials in the machine-readable campaign summary.
    log = tmp_path / "uvicorn.log"
    process = None
    started = time.monotonic()
    try:
        with log.open("wb") as output:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                ],
                cwd=root,
                env=environment,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False) as http:
            while True:
                assert process.poll() is None, "Actual application subprocess exited during startup"
                try:
                    readiness = http.get("/api/v1/ready")
                    if readiness.status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() - started < 30, "Actual application never became ready"
                time.sleep(0.1)
            csrf = http.get("/api/v1/auth/csrf")
            assert csrf.status_code == 200
            login = http.post(
                "/api/v1/auth/login",
                headers={"X-CSRF-Token": csrf.json()["csrf_token"]},
                json={
                    "account_kind": "employee",
                    "identifier": "EMP-ADMIN-941",
                    "password": "Staffpass123",
                },
            )
            assert login.status_code == 200, "Load fixture admin could not authenticate"
            assert login.json()["user"]["role"] == "admin"
            checks = {
                "/api/v1/health": lambda body: body["status"] == "ok",
                "/api/v1/ready": lambda body: body == {"status": "ready", "database": "up"},
                "/api/v1/auth/me": lambda body: body["user"]["role"] == "admin",
                "/api/v1/finance/dashboard": lambda body: isinstance(body, dict) and len(body) > 0,
                "/api/v1/orders": lambda body: any(
                    row["id"] == order["id"] for row in body["items"]
                ),
            }
            timings = defaultdict(list)
            errors = []
            paths = list(checks)
            began = time.monotonic()
            requests = 0
            while time.monotonic() - began < 300:
                path = paths[requests % len(paths)]
                request_started = time.monotonic()
                try:
                    result = http.get(path)
                    valid = result.status_code == 200 and checks[path](result.json())
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    valid = False
                timings[path].append((time.monotonic() - request_started) * 1000)
                if not valid:
                    errors.append(path)
                requests += 1
                # Fixed target 10 RPS; no catch-up burst after a slow response.
                time.sleep(max(0, 0.1 - (time.monotonic() - request_started)))
            elapsed = time.monotonic() - began
            summary = {
                "duration_seconds": elapsed,
                "requests": requests,
                "target_rps": 10,
                "actual_rps": requests / elapsed,
                "error_rate_percent": 100 * len(errors) / requests,
                "per_path": {
                    path: {
                        "requests": len(values),
                        "p95_ms": _percentile(values, 0.95),
                        "p99_ms": _percentile(values, 0.99),
                    }
                    for path, values in timings.items()
                },
                "limits": "local single-worker read workload; no stress/2x/long-soak certification",
            }
            print("LOAD_CAMPAIGN " + json.dumps(summary, sort_keys=True))
            assert elapsed >= 300 and requests >= 2700, summary
            assert summary["error_rate_percent"] < 0.1, summary
            for values in summary["per_path"].values():
                assert values["p95_ms"] <= 300 and values["p99_ms"] <= 800, summary
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
