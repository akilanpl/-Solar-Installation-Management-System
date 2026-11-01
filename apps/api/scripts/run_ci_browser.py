"""Reset ONLY local solarops_test, seed disposable accounts and run browser QA.

Requires an explicit SOLAROPS_TEST_DATABASE_URL and --reset-test-db. Run
sequentially with pytest; never against demo data. No seed password is printed.
"""

import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

API = Path(__file__).resolve().parents[1]
ROOT = API.parents[1]
sys.path.insert(0, str(API))


def restore_next_metadata(snapshots):
    """Restore only Next's known generated changes; retain unexpected edits."""
    for path, original in snapshots.items():
        current = path.read_bytes()
        if current == original:
            continue
        if path.name == "tsconfig.json":
            before, after = json.loads(original), json.loads(current)
            after["include"] = [
                item for item in after["include"] if item != ".next-ci-browser/types/**/*.ts"
            ]
            before["include"] = sorted(before["include"])
            after["include"] = sorted(after["include"])
            expected = before == after
        else:
            expected = (
                current.decode()
                .replace(".next-ci-browser/types/routes.d.ts", ".next/types/routes.d.ts")
                .splitlines()
                == original.decode().splitlines()
            )
        if not expected:
            raise RuntimeError("Unexpected Next metadata edit preserved for review")
        path.write_bytes(original)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset-test-db", action="store_true", required=True)
    parser.add_argument("--grep")
    parser.add_argument("--repeat-each", type=int, default=1)
    parser.add_argument("--junit", type=Path)
    args = parser.parse_args()
    raw = os.environ.get("SOLAROPS_TEST_DATABASE_URL")
    if not raw:
        raise SystemExit("Set an explicit local disposable SOLAROPS_TEST_DATABASE_URL.")
    target = make_url(raw)
    if target.database != "solarops_test" or target.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Browser QA only permits local solarops_test.")
    if args.repeat_each < 1:
        raise SystemExit("repeat-each must be positive.")
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required.")
    for port in (8011, 3011):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Isolated browser ports are in use; stop the prior QA run first.")
    os.chdir(API)

    from app.core.security import hash_password, utcnow
    from app.models.identity import CustomerProfile, EmployeeProfile, User
    from tests.conftest import _assert_safe, _migrate

    from local_secrets import protect
    from seed_demo import ACCOUNTS
    from seed_dev import STAFF

    _assert_safe(raw)
    engine = create_engine(raw)
    try:
        with engine.connect() as db:
            other_sessions = db.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND pid<>pg_backend_pid()"
                )
            ).scalar_one()
            if other_sessions:
                raise SystemExit("Disposable database is in use; stop other test processes first.")
    finally:
        engine.dispose()
    _migrate()
    password = "BrowserQA-2026-" + secrets.token_urlsafe(18)
    credentials = {}
    engine = create_engine(raw)
    try:
        with Session(engine) as db:
            for email, code, name, phone, role in STAFF:
                user = User(
                    email=email,
                    password_hash=hash_password(password),
                    role_code=role,
                    email_verified_at=utcnow(),
                    is_active=True,
                )
                db.add(user)
                db.flush()
                db.add(
                    EmployeeProfile(
                        user_id=user.id, employee_code=code, full_name=name, phone=phone
                    )
                )
            for role, email, code, name, phone in ACCOUNTS:
                user = User(
                    email=email,
                    password_hash=hash_password(password),
                    role_code=role,
                    email_verified_at=utcnow(),
                    is_active=True,
                )
                db.add(user)
                db.flush()
                db.add(
                    EmployeeProfile(
                        user_id=user.id, employee_code=code, full_name=name, phone=phone
                    )
                    if code
                    else CustomerProfile(user_id=user.id, full_name=name, phone=phone)
                )
                credentials[email] = {
                    "role": role,
                    "identifier": code or email,
                    "password": password,
                }
            db.commit()
    finally:
        engine.dispose()
    run = ROOT / "var/pr-browser" / datetime.now(UTC).strftime("browser-%Y%m%dT%H%M%S%fZ")
    run.mkdir(parents=True)
    protect(run)
    credentials_file = run / "credentials.json"
    credentials_file.write_text(json.dumps(credentials), encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        SOLAROPS_E2E_DATABASE_URL=raw,
        SOLAROPS_DATABASE_URL=raw,
        SOLAROPS_APP_ENV="development",
        SOLAROPS_COOKIE_SECURE="false",
        SOLAROPS_SECRET_KEY=secrets.token_urlsafe(48),
        SOLAROPS_SMTP_HOST="",
        SOLAROPS_TRUSTED_ORIGINS="http://127.0.0.1:3011",
        SOLAROPS_MAILBOX_PATH=str(run / "mailbox.jsonl"),
        SOLAROPS_EVIDENCE_DIR=str(run / "survey-evidence"),
        SOLAROPS_SEED_PASSWORD=password,
        SOLAROPS_API_ORIGIN="http://127.0.0.1:8011",
        NEXT_PUBLIC_SOLAROPS_ENV="development",
        NEXT_TELEMETRY_DISABLED="1",
        SOLAROPS_E2E_OUTPUT_DIR=str(run / "test-results"),
        SOLAROPS_E2E_CREDENTIALS_FILE=str(credentials_file),
        SOLAROPS_NEXT_DIST_DIR=".next-ci-browser",
        PLAYWRIGHT_JSON_OUTPUT_NAME=str(run / "results.json"),
        PLAYWRIGHT_JUNIT_OUTPUT_NAME=str(args.junit or run / "browser.xml"),
    )
    command = [
        node,
        "node_modules/@playwright/test/cli.js",
        "test",
        "--config=playwright.gate.config.ts",
        "--reporter=line,json,junit",
        f"--repeat-each={args.repeat_each}",
    ]
    if args.grep:
        command.extend(["--grep", args.grep])
    print("Disposable browser staff ready; using isolated ports 8011/3011.", flush=True)
    snapshots = {
        ROOT / "apps/web" / name: (ROOT / "apps/web" / name).read_bytes()
        for name in ("tsconfig.json", "next-env.d.ts")
    }
    try:
        return subprocess.run(
            command, cwd=ROOT / "apps/web", env=environment, check=False
        ).returncode
    finally:
        restore_next_metadata(snapshots)


if __name__ == "__main__":
    raise SystemExit(main())
