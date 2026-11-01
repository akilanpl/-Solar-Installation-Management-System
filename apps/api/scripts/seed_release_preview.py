"""Provision staff only in a separately named local development preview DB."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import Settings
from app.core.security import hash_password, utcnow
from app.db.session import build_engine
from app.models.identity import EmployeeProfile, User
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from seed_dev import STAFF, password_from_env


def main():
    settings = Settings()
    target = make_url(settings.database_url)
    if settings.app_env != "development" or target.host not in {"localhost", "127.0.0.1"} or not re.fullmatch(r"solarops_release_demo_[0-9]{8}", target.database or ""):
        raise SystemExit("Requires development and a local solarops_release_demo_YYYYMMDD database.")
    password = password_from_env(settings)
    engine = build_engine(settings.database_url)
    with Session(engine) as db:
        for email, code, name, phone, role in STAFF:
            if db.scalar(select(User.id).where(User.email == email)):
                continue
            user = User(email=email, password_hash=hash_password(password), role_code=role, email_verified_at=utcnow(), is_active=True)
            db.add(user)
            db.flush()
            db.add(EmployeeProfile(user_id=user.id, employee_code=code, full_name=name, phone=phone))
        db.commit()
    engine.dispose()
    print("Preview staff provisioned. No customer/order/payment/delivery records fabricated.")


if __name__ == "__main__":
    main()
