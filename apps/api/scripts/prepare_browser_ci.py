"""Migrate an EMPTY explicitly disposable browser DB; seed staff, never business records."""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import Settings
from app.core.security import hash_password, utcnow
from app.db.session import build_engine
from app.models.identity import EmployeeProfile, User
from sqlalchemy import inspect, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from seed_dev import STAFF


def validate_target(url: str, env: dict[str, str]) -> None:
    target = make_url(url)
    if (env.get("SOLAROPS_APP_ENV") != "development"
        or target.host not in {"127.0.0.1", "localhost"}
        or not re.fullmatch(r"solarops_browser_ci(?:_[a-f0-9]{12})?", target.database or "")
        or target.database != env.get("SOLAROPS_BROWSER_DATABASE_NAME")):
        raise ValueError("Requires an explicitly named local solarops_browser_ci disposable database.")
    if any(env.get(key) for key in (
        "SOLAROPS_RAZORPAY_KEY_ID", "SOLAROPS_RAZORPAY_KEY_SECRET",
        "SOLAROPS_RAZORPAY_WEBHOOK_SECRET", "SOLAROPS_SMTP_HOST",
    )):
        raise ValueError("External payment and email providers must be unset.")
    if len(env.get("SOLAROPS_SEED_PASSWORD", "")) < 16:
        raise ValueError("Supply a fresh ephemeral staff password of at least 16 characters.")


def main() -> None:
    validate_target(os.environ["SOLAROPS_DATABASE_URL"], dict(os.environ))
    # Disable private .env loading; CI must be completely described by its environment.
    settings = Settings(_env_file=None)
    if settings.razorpay_key_id or settings.smtp_host:
        raise ValueError("External providers must be disabled.")
    engine = build_engine(settings.database_url)
    if inspect(engine).get_table_names():
        raise ValueError("Database is not empty; refusing to reuse or erase existing records.")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    with Session(engine) as db:
        for email, code, name, phone, role in STAFF:
            user = User(email=email, password_hash=hash_password(os.environ["SOLAROPS_SEED_PASSWORD"]),
                        role_code=role, email_verified_at=utcnow(), is_active=True)
            db.add(user)
            db.flush()
            db.add(EmployeeProfile(user_id=user.id, employee_code=code, full_name=name, phone=phone))
        db.commit()
        assert len(list(db.scalars(select(User)))) == len(STAFF)
    engine.dispose()
    print("Migrated empty browser database; staff only. Customer and lifecycle must be created by acceptance.")


if __name__ == "__main__":
    main()
