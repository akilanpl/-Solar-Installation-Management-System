"""Reset/seed ONLY solarops_test and run browser QA on isolated ports/builds.

Requires existing ignored demo credentials from the local Phase 1 setup.
Never migrates or seeds solarops_dev. Do not run concurrently with pytest.
Development mode on the isolated API enables the existing test mailbox only;
authentication, CSRF and role enforcement remain active.
"""

import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1]
ROOT = API.parents[1]
sys.path.insert(0, str(API))

from app.core.security import hash_password, utcnow  # noqa: E402
from app.models.identity import CustomerProfile, EmployeeProfile, User  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from tests.conftest import TEST_DATABASE_URL, _assert_safe, _migrate  # noqa: E402

from seed_demo import ACCOUNTS  # noqa: E402
from seed_dev import STAFF  # noqa: E402


def main() -> int:
    _assert_safe(TEST_DATABASE_URL)
    if make_url(TEST_DATABASE_URL).host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Browser QA requires a local disposable test database.")
    credentials_file = ROOT / "var/demo-credentials.json"
    staff_file = ROOT / "var/dev-seed-password.txt"
    if not credentials_file.is_file() or not staff_file.is_file():
        raise SystemExit(
            "Local demo credential files are missing; complete LOCAL_POSTGRESQL.md setup first."
        )
    credentials = json.loads(credentials_file.read_text(encoding="utf-8"))
    staff_password = staff_file.read_text(encoding="utf-8").strip()
    _migrate()
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with Session(engine) as db:
            for role, email, code, name, phone in ACCOUNTS:
                user = User(
                    email=email,
                    role_code=role,
                    is_active=True,
                    email_verified_at=utcnow(),
                    password_hash=hash_password(credentials[email]["password"]),
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
            for email, code, name, phone, role in STAFF:
                user = User(
                    email=email,
                    role_code=role,
                    is_active=True,
                    email_verified_at=utcnow(),
                    password_hash=hash_password(staff_password),
                )
                db.add(user)
                db.flush()
                db.add(
                    EmployeeProfile(
                        user_id=user.id, employee_code=code, full_name=name, phone=phone
                    )
                )
            db.commit()
    finally:
        engine.dispose()
    print("Isolated browser accounts prepared in solarops_test; development data untouched.")
    environment = os.environ.copy()
    environment.update(
        SOLAROPS_E2E_DATABASE_URL=TEST_DATABASE_URL,
        SOLAROPS_SEED_PASSWORD=staff_password,
        SOLAROPS_SECRET_KEY=secrets.token_urlsafe(48),
    )
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise SystemExit("npm is not available.")
    return subprocess.run(
        [npm, "run", "e2e", "--", "--config=playwright.qa.config.ts", "--workers=1"],
        cwd=ROOT / "apps/web",
        env=environment,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
