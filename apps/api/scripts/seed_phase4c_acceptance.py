"""Seed ONLY the dedicated, empty Phase 4C preview database with synthetic data.

Reuses inherited workflow test drivers to create real accepted orders, delivery,
installation signatures and an accepted Phase 4B bill. Never simulates providers.
Run after Alembic upgrade. Refuses all other database names and nonempty previews.
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api"))
os.environ["SOLAROPS_EVIDENCE_DIR"] = str(ROOT / "var/phase4c/uploads")
os.environ.setdefault(
    "SOLAROPS_DATABASE_URL", "postgresql+psycopg://akilan@127.0.0.1:5432/solarops_4c_preview"
)
os.environ.setdefault("SOLAROPS_SECRET_KEY", "phase4c-preview-local-secret-not-production")
os.environ["SOLAROPS_TEST_DATABASE_URL"] = (
    "postgresql+psycopg://akilan@127.0.0.1:5432/solarops_release_test_20261113"
)
os.environ["SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME"] = "solarops_release_test_20261113"

from app.core.config import Settings, get_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.identity import User  # noqa: E402
from app.models.phase3 import InstallationJob, StockLedger, StockOperation  # noqa: E402
from app.models.workflow import PaymentIntent, SalesOrder  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from tests.test_phase3_warehouse_installation import _uploaded_photo  # noqa: E402
from tests.test_phase4a_support import _all_staff, _installed_order, _login, _tech_id  # noqa: E402
from tests.test_phase4b_billing import _estimate, _ready_flow  # noqa: E402
from tests.test_phase4c_finance import post, upload  # noqa: E402


def main():
    url = os.environ.get(
        "SOLAROPS_PHASE4C_PREVIEW_URL",
        "postgresql+psycopg://akilan@127.0.0.1:5432/solarops_4c_preview",
    )
    parsed = make_url(url)
    if parsed.database != "solarops_4c_preview" or parsed.host != "127.0.0.1":
        raise SystemExit("Refusing a database outside the isolated Phase 4C preview.")
    # Test helper imports initialize test defaults. Restore the preview identity
    # before any request so global inherited dependencies match this app factory.
    os.environ["SOLAROPS_DATABASE_URL"] = url
    os.environ["SOLAROPS_SECRET_KEY"] = "phase4c-preview-local-secret-not-production"
    os.environ["SOLAROPS_APP_ENV"] = "test"
    get_settings.cache_clear()
    settings = Settings(
        app_env="test",
        database_url=url,
        secret_key="phase4c-preview-local-secret-not-production",
        cookie_secure=False,
        login_ip_limit=1000,
        login_identifier_limit=1000,
        evidence_dir=str(ROOT / "var/phase4c/uploads"),
    )
    app = create_app(settings)
    with Session(app.state.engine) as db:
        if db.scalar(select(func.count()).select_from(User)):
            raise SystemExit("Preview is nonempty. Preserve it; use the existing manifest.")
    with TestClient(app) as client:
        _all_staff(app)
        ticket, _, order = _ready_flow(client, app, labour_covered=False)
        estimate = _estimate(client, ticket["id"]).json()
        customer = _login(client, "customer", "leela@example.com", "Solarops123")
        accepted = client.post(
            f"/api/v1/estimates/{estimate['id']}/decision",
            json={"decision": "accepted", "estimate_version": estimate["version"]},
            headers=customer,
        )
        assert accepted.status_code == 200, accepted.text
        support = _login(client, "employee", "EMP-SUP-901", "Staffpass123")
        source = client.post(
            "/api/v1/service-invoices",
            json={"estimate_id": estimate["id"]},
            headers={**support, "Idempotency-Key": "preview-service-invoice"},
        )
        assert source.status_code == 201, source.text
        with Session(app.state.engine) as db:
            source_order = db.get(SalesOrder, __import__("uuid").UUID(ticket["order_id"]))
            order = {
                "id": str(source_order.id),
                "total_minor": source_order.total_minor,
                "tax_minor": source_order.tax_minor,
                "reference": source_order.reference,
            }
        technician_id = _tech_id(app, "tech@example.com")
        orders = [
            order,
            _installed_order(client, app, "loss@example.com", "PHASE4C-LOSS-SERIAL")[0],
        ]
        jobs = []
        for index, order in enumerate(orders):
            sales = _login(client, "employee", "EMP-SALES-901", "Staffpass123")
            response = client.post(
                "/api/v1/jobs",
                json={"order_id": order["id"], "technician_user_id": technician_id},
                headers=sales,
            )
            assert response.status_code == 201, response.text
            job = response.json()
            code = app.state.email_sender.messages[-1].code
            tech = _login(client, "employee", "EMP-TECH-901", "Staffpass123")
            path = f"/api/v1/jobs/{job['id']}"
            assert client.post(path + "/arrival", headers=tech).status_code == 200
            photo = _uploaded_photo(client, job["id"], tech)
            now = datetime.now(UTC)
            response = client.post(
                path + "/evidence",
                json={
                    "photo_refs": [photo],
                    "installed_capacity_kw": "3",
                    "test_readings": {"voc_v": 612},
                    "started_at": (now - timedelta(minutes=1)).isoformat(),
                    "finished_at": now.isoformat(),
                },
                headers=tech,
            )
            assert response.status_code == 200, response.text
            email = "leela@example.com" if index == 0 else "loss@example.com"
            customer = _login(client, "customer", email, "Solarops123")
            summary = client.get(path + "/work-summary").json()
            assert (
                client.post(
                    path + "/signature",
                    json={
                        "signature_ref": "SYNTHETIC LOCAL CUSTOMER",
                        "customer_confirmed": True,
                        "summary_hash": summary["summary_hash"],
                    },
                    headers=customer,
                ).status_code
                == 200
            )
            tech = _login(client, "employee", "EMP-TECH-901", "Staffpass123")
            refreshed = client.get(path + "/work-summary").json()
            assert refreshed == summary, {"before": summary, "after": refreshed}
            assert (
                client.post(path + "/customer-otp", json={"code": code}, headers=tech).status_code
                == 200
            )
            completion = client.post(path + "/completion", headers=tech)
            assert completion.status_code == 200, completion.text
            jobs.append(job)
        headers = _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")
        ev = upload(client, headers)
        post(client, "periods", {"starts_on": "2020-01-01", "ends_on": "2040-12-31"}, headers)
        policy = post(
            client,
            "policies",
            {
                "key": "preview-policy",
                "label": "SYNTHETIC LOCAL accounting approval",
                "approval_reference": "TEST FIXTURE ONLY no real business approval",
                "effective_from": "2020-01-01",
                "effective_to": "2040-12-31",
                "recognition": "completed_installation_and_approved_service",
                "tax": "preserve_approved_source_snapshot",
                "posting_rules": "invoice_deferred_tax_on_issue_costs_on_approval",
            },
            headers,
        )
        now = datetime.now(UTC)
        post(
            client,
            "labour-rates",
            {
                "key": "preview-rate",
                "technician_id": technician_id,
                "hourly_minor": 6000,
                "effective_from": (now - timedelta(days=1)).isoformat(),
                "effective_to": (now + timedelta(days=1)).isoformat(),
                "evidence_id": ev,
            },
            headers,
        )
        # Synthetic clock span for the labour acceptance scenario; no production source is touched.
        with Session(app.state.engine) as db:
            job = db.get(InstallationJob, __import__("uuid").UUID(jobs[0]["id"]))
            job.arrival_at = now - timedelta(hours=1)
            job.completed_at = now
            db.commit()
        tech = _login(client, "employee", "EMP-TECH-901", "Staffpass123")
        sheet = post(
            client,
            "timesheets",
            {
                "key": "preview-sheet",
                "job_kind": "installation",
                "job_id": jobs[0]["id"],
                "check_in": (now - timedelta(hours=1)).isoformat(),
                "check_out": now.isoformat(),
                "note": "Synthetic acceptance work interval",
            },
            tech,
        )
        headers = _login(client, "employee", "EMP-ADMIN-941", "Staffpass123")
        scheme = post(
            client,
            "subsidy-schemes",
            {
                "key": "preview-checklist",
                "name": "SYNTHETIC official checklist fixture",
                "official_url": "https://example.gov.in/synthetic-checklist",
                "version": "LOCAL TEST VERSION",
                "effective_from": "2020-01-01",
                "effective_to": "2040-12-31",
                "required_documents": ["identity", "electricity_bill"],
                "evidence_id": ev,
            },
            headers,
        )
        with Session(app.state.engine) as db:
            ledgers = {
                str(o["id"]): [
                    str(row.id)
                    for row in db.scalars(
                        select(StockLedger)
                        .join(StockOperation, StockOperation.id == StockLedger.operation_id)
                        .where(
                            StockOperation.source_order_id == __import__("uuid").UUID(o["id"]),
                            StockLedger.quantity_delta < 0,
                        )
                    )
                ]
                for o in orders
            }
        with Session(app.state.engine) as db:
            payments = {
                o["id"]: str(
                    db.scalar(
                        select(PaymentIntent.id)
                        .join(SalesOrder, SalesOrder.quotation_id == PaymentIntent.quotation_id)
                        .where(
                            SalesOrder.id == __import__("uuid").UUID(o["id"]),
                            PaymentIntent.status == "verified",
                        )
                    )
                )
                for o in orders
            }
        manifest = {
            "payments": payments,
            "orders": orders,
            "jobs": jobs,
            "ledgers": ledgers,
            "policy_id": policy["id"],
            "evidence_id": ev,
            "sheet_id": sheet["id"],
            "scheme_id": scheme["id"],
            "service_invoice": source.json(),
            "seed_note": "Entirely synthetic local fixtures; no real approvals, charges or settlements.",
        }
        path = ROOT / "var/phase4c/acceptance-manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        print("Created isolated synthetic preview manifest:", path)
    app.state.engine.dispose()


if __name__ == "__main__":
    main()
