"""Populate only the empty, explicitly owned release-browser CI database.

Real production commands create saved records; test helpers supply synthetic
clock/evidence inputs. No external provider, payment or physical work is claimed.
Never drops a schema or reads local demo credentials.
"""
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api"))


def assert_safe(environment):
    url = make_url(environment.get("SOLAROPS_DATABASE_URL", ""))
    if (url.host not in {"127.0.0.1", "localhost"}
            or url.database != "solarops_browser_release_ci"
            or environment.get("SOLAROPS_RELEASE_DATABASE_OWNED") != "true"
            or environment.get("SOLAROPS_APP_ENV") != "development"):
        raise ValueError("Requires explicitly owned local release-browser CI database")
    if any(environment.get(key) for key in (
        "SOLAROPS_RAZORPAY_KEY_ID", "SOLAROPS_RAZORPAY_KEY_SECRET",
        "SOLAROPS_RAZORPAY_WEBHOOK_SECRET", "SOLAROPS_SMTP_HOST",
    )):
        raise ValueError("External email/payment integrations forbidden in release fixtures")
    return url


def main():
    environment = dict(os.environ)
    assert_safe(environment)
    engine = create_engine(environment["SOLAROPS_DATABASE_URL"])
    with engine.connect() as connection:
        if connection.scalar(text("SELECT count(*) FROM users")):
            raise ValueError("Nonempty release fixture database preserved; use a fresh database")
    engine.dispose()
    # Helper imports initialize pytest defaults. Restore the explicitly checked
    # target before constructing the real app; never invoke pytest reset fixtures.
    from app.core.config import Settings, get_settings
    from app.core.security import hash_password, utcnow
    from app.main import create_app
    from app.models.identity import EmployeeProfile, User
    from app.models.phase3 import EquipmentSerial
    from app.models.workflow import SalesOrder
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from tests.test_phase4a_support import _all_staff, _login, _order_material, _receipt_validate
    from tests.test_phase4b_billing import _estimate, _ready_flow
    from tests.test_phase4b_replacement import _propose

    from seed_dev import STAFF

    os.environ.update(environment)
    get_settings.cache_clear()
    settings = Settings(_env_file=None, **{
        "app_env": "test", "database_url": environment["SOLAROPS_DATABASE_URL"],
        "secret_key": environment["SOLAROPS_SECRET_KEY"], "cookie_secure": False,
        "evidence_dir": environment["SOLAROPS_EVIDENCE_DIR"],
        "login_ip_limit": 1000, "login_identifier_limit": 1000,
    })
    app = create_app(settings)
    password = environment["SOLAROPS_SEED_PASSWORD"]
    accounts = []
    with Session(app.state.engine) as db:
        for email, code, name, phone, role in [*STAFF,
                ("mfa@synthetic.example", "EMP-TECH-4E", "Synthetic MFA", "9845000000", "technician")]:
            user = User(email=email, password_hash=hash_password(password), role_code=role,
                        email_verified_at=utcnow(), is_active=True)
            db.add(user)
            db.flush()
            db.add(EmployeeProfile(user_id=user.id, employee_code=code, full_name=name, phone=phone))
            accounts.append({"role": role, "identifier": code, "password": password})
        db.commit()
    with TestClient(app) as client:
        _all_staff(app)
        ticket, job, _ = _ready_flow(client, app, labour_covered=False)
        order = {"id": ticket["order_id"]}
        estimate_response = _estimate(client, ticket["id"])
        assert estimate_response.status_code == 201, estimate_response.text
        estimate = estimate_response.json()
        customer = _login(client, "customer", "leela@example.com", "Solarops123")
        response = client.post(f"/api/v1/estimates/{estimate['id']}/decision",
            json={"decision": "accepted", "estimate_version": estimate["version"]}, headers=customer)
        assert response.status_code == 200, response.text
        support = _login(client, "employee", "EMP-SUP-901", "Staffpass123")
        response = client.post("/api/v1/service-invoices", json={"estimate_id": estimate["id"]},
            headers={**support, "Idempotency-Key": "synthetic-release-invoice"})
        assert response.status_code == 201, response.text
        invoice = response.json()
        warehouse = _login(client, "employee", "EMP-WH-901", "Staffpass123")
        component = _order_material(app, order["id"])[0][0]
        receipt = _receipt_validate(client, warehouse, component, "1.0000", "MAIN")
        response = client.post("/api/v1/serials/scan", json={
            "serial_number": "TEST-RELEASE-REPLACEMENT", "component_code": component,
            "operation_id": receipt["id"]}, headers=warehouse)
        assert response.status_code == 201, response.text
        with Session(app.state.engine) as db:
            old = db.scalar(select(EquipmentSerial.serial_number).where(
                EquipmentSerial.order_id == order["id"], EquipmentSerial.status == "installed"))
        response = _propose(client, ticket["id"], old, "TEST-RELEASE-REPLACEMENT")
        assert response.status_code == 201, response.text
        replacement = response.json()
        with Session(app.state.engine) as db:
            saved = db.get(SalesOrder, __import__("uuid").UUID(order["id"]))
            ids = {"enquiries": str(saved.enquiry_id), "orders": str(saved.id),
                   "quotations": str(saved.quotation_id), "surveys": str(saved.survey_id),
                   "complaints": ticket["id"], "tickets": ticket["id"], "repairs": job["id"],
                   "estimates": estimate["id"], "bills": invoice["id"], "replacements": replacement["id"]}
    # Access audits must use the record owner and assigned technician, not fake IDs.
    for role, identifier in [("customer", "leela@example.com"), ("technician", "EMP-TECH-901")]:
        accounts = [a for a in accounts if a["role"] != role]
        accounts.append({"role": role, "identifier": identifier,
                         "password": "Solarops123" if role == "customer" else "Staffpass123"})
    accounts.append({"role": "mfa", "identifier": "EMP-TECH-4E", "password": password})
    mapping = {}
    for page in (ROOT / "apps/web/src/app").rglob("page.tsx"):
        route = "/" + "/".join(page.parent.relative_to(ROOT / "apps/web/src/app").parts)
        if "[id]" in route:
            kind = route.split("/")[-2]
            if kind not in ids:
                raise ValueError(f"Unpopulated route: {route}")
            mapping[route] = route.replace("[id]", ids[kind])
    for name, value in [("browser-fixtures.json", mapping),
            ("LOCAL_PREVIEW_ACCOUNTS.txt", {"environment": "development", "accounts": accounts})]:
        path = Path(environment["SOLAROPS_RELEASE_FIXTURE_DIR"]) / name
        path.parent.mkdir(exist_ok=True, mode=0o700)
        path.parent.chmod(0o700)
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
            output.write(json.dumps(value) + "\n")
    app.state.engine.dispose()
    print(f"Prepared {len(mapping)} persisted dynamic routes in isolated synthetic database")


if __name__ == "__main__":
    main()
