"""Development seed for staff accounts.

Catalogue packages and roles come from the Alembic migration. This script
creates employee logins only. It refuses to run unless the database name is
`solarops_dev` and the environment is development. Passwords are never written
into the repository. If SOLAROPS_SEED_PASSWORD is unset, a password is
generated into var/dev-seed-password.txt.
"""

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import REPO_ROOT, Settings
from app.core.security import hash_password, utcnow
from app.db.session import build_engine, build_session_factory
from app.models.identity import EmployeeProfile, User
from app.repositories.queries import get_user_by_email
from sqlalchemy.engine.url import make_url

from local_secrets import protect

STAFF = [
    ("admin@sunpower.example", "EMP-ADMIN-001", "Asha Menon", "9845011111", "admin"),
    ("sales@sunpower.example", "EMP-SALES-001", "Rahul Iyer", "9845022222", "sales"),
    ("tech@sunpower.example", "EMP-TECH-001", "Kavya Rao", "9845033333", "technician"),
    ("warehouse@sunpower.example", "EMP-WH-001", "Imran Sheikh", "9845044444", "warehouse_staff"),
    ("whmanager@sunpower.example", "EMP-WHM-001", "Divya Nair", "9845055555", "warehouse_manager"),
    ("support@sunpower.example", "EMP-SUP-001", "Meera Krishnan", "9845066666", "support"),
]


def password_from_env(settings: Settings) -> str:
    if settings.seed_password:
        if len(settings.seed_password) < 10:
            raise SystemExit("SOLAROPS_SEED_PASSWORD must be at least 10 characters.")
        return settings.seed_password
    path = REPO_ROOT / "var" / "dev-seed-password.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    generated = f"Solarops-{secrets.token_urlsafe(9)}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generated + "\n", encoding="utf-8")
    protect(path)
    print(f"Wrote a development staff password to {path}")
    return generated


def main() -> None:
    settings = Settings()
    url = make_url(settings.database_url)
    database = url.database
    if (
        settings.app_env != "development"
        or database != "solarops_dev"
        or url.host not in {"127.0.0.1", "localhost"}
    ):
        raise SystemExit(
            f"Refusing to seed app_env={settings.app_env} database={database}. "
            "This command only runs for the local development database named solarops_dev."
        )
    password = password_from_env(settings)
    engine = build_engine(settings.database_url)
    factory = build_session_factory(engine)
    db = factory()
    created = 0
    try:
        for email, code, name, phone, role in STAFF:
            if get_user_by_email(db, email) is not None:
                continue
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
                    user_id=user.id,
                    employee_code=code,
                    full_name=name,
                    phone=phone,
                )
            )
            created += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()
    print(f"Seed complete. New staff accounts: {created}. Existing accounts were left unchanged.")
    print("Employee IDs: " + ", ".join(row[1] for row in STAFF))


if __name__ == "__main__":
    main()
