"""Idempotent demo data for local solarops_dev, using normal domain services.

Accounts are development-only preverified factories, not an auth bypass.
Generated passwords stay in gitignored var/demo-credentials.json.
"""

import json
import re
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import REPO_ROOT, Settings
from app.core.security import hash_password, utcnow, verify_password
from app.db.session import build_engine, build_session_factory
from app.models.identity import CustomerProfile, EmployeeProfile, User
from app.repositories.queries import add_audit, get_user_by_email
from app.schemas import EmployeeCreate, EnquiryCreate, QualificationUpdate, SignupRequest
from app.services.enquiry_service import create_enquiry, qualify_enquiry
from sqlalchemy.engine.url import make_url

from local_secrets import protect

ACCOUNTS = [
    ("customer", "customer.demo@solarops.example.com", None, "Leela Nair", "9845099999"),
    ("customer", "commercial.demo@solarops.example.com", None, "Arjun Retail", "9845099998"),
    ("customer", "industrial.demo@solarops.example.com", None, "Kavya Engineering", "9845099997"),
    ("sales", "sales.demo@solarops.example.com", "EMP-SALES-DEMO-001", "Rahul Iyer", "9845099996"),
    ("admin", "admin.demo@solarops.example.com", "EMP-ADMIN-DEMO-001", "Asha Menon", "9845099995"),
]
CREDENTIALS = REPO_ROOT / "var" / "demo-credentials.json"


def assert_development(settings: Settings) -> None:
    url = make_url(settings.database_url)
    if (
        settings.app_env != "development"
        or not (url.database == "solarops_dev" or re.fullmatch(r"solarops_release_demo_[0-9]{8}", url.database or ""))
        or url.host not in {"127.0.0.1", "localhost"}
    ):
        raise SystemExit("Demo seeding requires development mode and a local explicitly named development/preview database.")


def main() -> None:
    settings = Settings()
    assert_development(settings)
    CREDENTIALS.parent.mkdir(parents=True, exist_ok=True)
    protect(CREDENTIALS.parent)
    if CREDENTIALS.exists():
        credentials = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
    else:
        credentials = {
            email: {
                "role": role,
                "identifier": code or email,
                "password": f"SolarDemo9-{secrets.token_urlsafe(18)}",
            }
            for role, email, code, _name, _phone in ACCOUNTS
        }
        CREDENTIALS.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIALS.write_text(json.dumps(credentials, indent=2) + "\n", encoding="utf-8")
        protect(CREDENTIALS)
    engine = build_engine(settings.database_url)
    factory = build_session_factory(engine)
    created_accounts = created_enquiries = 0
    try:
        with factory.begin() as db:
            users = {}
            for role, email, code, name, phone in ACCOUNTS:
                password = credentials[email]["password"]
                common = dict(email=email, full_name=name, phone=phone, password=password)
                if code:
                    EmployeeCreate(**common, employee_code=code, role=role)
                else:
                    SignupRequest(**common)
                user = get_user_by_email(db, email)
                if user is None:
                    user = User(
                        email=email,
                        password_hash=hash_password(password),
                        role_code=role,
                        email_verified_at=utcnow(),
                        is_active=True,
                    )
                    db.add(user)
                    db.flush()
                    profile = (
                        EmployeeProfile(
                            user_id=user.id, employee_code=code, full_name=name, phone=phone
                        )
                        if code
                        else CustomerProfile(user_id=user.id, full_name=name, phone=phone)
                    )
                    db.add(profile)
                    add_audit(
                        db,
                        actor_user_id=user.id,
                        action="demo.account_seeded",
                        entity_type="user",
                        entity_id=user.id,
                        metadata={"role": role},
                    )
                    db.flush()
                    created_accounts += 1
                elif (
                    user.role_code != role
                    or not user.is_active
                    or not user.email_verified_at
                    or not verify_password(user.password_hash, password)
                ):
                    raise SystemExit(
                        "Existing demo account differs from stored credentials; refusing to overwrite it."
                    )
                users[email] = user
            samples = [
                (
                    0,
                    "chennai-new",
                    "submitted",
                    "18 Lake View Road",
                    "Chennai",
                    "Tamil Nadu",
                    "600042",
                    3000,
                    480000,
                    "on_grid",
                    None,
                ),
                (
                    1,
                    "hyderabad-review",
                    "under_review",
                    "42 Madhapur Market Road",
                    "Hyderabad",
                    "Telangana",
                    "500081",
                    5000,
                    1800000,
                    "on_grid",
                    "Commercial rooftop: check shade and sanctioned load.",
                ),
                (
                    2,
                    "bengaluru-qualified",
                    "qualified",
                    "7 Peenya Industrial Estate",
                    "Bengaluru",
                    "Karnataka",
                    "560058",
                    5000,
                    3200000,
                    "on_grid",
                    "Pilot rooftop section approved for detailed survey.",
                ),
                (
                    0,
                    "chennai-declined",
                    "not_qualified",
                    "19 Lake View Road",
                    "Chennai",
                    "Tamil Nadu",
                    "600042",
                    2000,
                    250000,
                    "off_grid",
                    "Roof structure requires reinforcement before installation.",
                ),
            ]
            sales = users[ACCOUNTS[3][1]]
            for owner, key, status, line1, city, state, pin, capacity, bill, grid, note in samples:
                _role, email, _code, name, phone = ACCOUNTS[owner]
                payload = EnquiryCreate(
                    contact_name=name,
                    contact_phone=phone,
                    contact_email=email,
                    site={"line1": line1, "city": city, "state": state, "postal_code": pin},
                    preferred_capacity_w=capacity,
                    grid_preference=grid,
                    monthly_bill_minor=bill,
                    subsidy_interest=owner == 0,
                )
                enquiry, replayed = create_enquiry(db, users[email], payload, f"demo-{key}-v1")
                if not replayed:
                    created_enquiries += 1
                    if status != "submitted":
                        qualify_enquiry(
                            db, sales, enquiry.id, QualificationUpdate(status=status, note=note, shadow_free_area_sqm=40 if status == "qualified" else None, grid_connection_suitable=True if status == "qualified" else None)
                        )
    finally:
        engine.dispose()
    print(
        f"Demo seed complete: {created_accounts} new accounts, {created_enquiries} new enquiries."
    )
    print(f"Credentials stored locally at {CREDENTIALS}; passwords are not printed.")


if __name__ == "__main__":
    main()
