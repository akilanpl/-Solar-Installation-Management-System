"""Read-only independent database oracle after the browser campaign."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import build_engine
from sqlalchemy import text

from prepare_browser_ci import validate_target


def main():
    validate_target(os.environ["SOLAROPS_DATABASE_URL"], dict(os.environ))
    root = Path(__file__).resolve().parents[3]
    records = json.loads((root / "var/browser-ci/records.json").read_text())
    engine = build_engine(os.environ["SOLAROPS_DATABASE_URL"])
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY"))
        def row(sql, **params):
            result = connection.execute(text(sql), params).mappings().one()
            return dict(result)
        order = row("SELECT id, customer_user_id, quotation_id FROM sales_orders WHERE id=:id", id=records["order"])
        assert str(order["quotation_id"]) == records["quote"]
        job = row("SELECT status, order_id, evidence, signature, otp_verified FROM installation_jobs WHERE id=:id", id=records["installation"])
        assert job["status"] == "completed" and job["otp_verified"] and job["evidence"] and job["signature"]
        assert str(job["order_id"]) == records["order"]
        ticket = row("SELECT status, order_id, customer_user_id FROM service_tickets WHERE id=:id", id=records["ticket"])
        assert ticket["status"] == "closed"
        assert ticket["customer_user_id"] == order["customer_user_id"]
        assert str(ticket["order_id"]) == records["order"]
        payment = row("SELECT status, is_test_only, method, quotation_id FROM payment_intents WHERE id=:id", id=records["payment"])
        assert payment["status"] == "verified" and payment["is_test_only"] and payment["method"] == "sandbox"
        assert str(payment["quotation_id"]) == records["quote"]
        assert row("SELECT count(*) AS n FROM payment_intents WHERE quotation_id=:id", id=records["quote"])["n"] == 1
        assert row("SELECT count(*) AS n FROM sales_orders WHERE quotation_id=:id", id=records["quote"])["n"] == 1
        repair = row("SELECT status, ticket_id FROM ticket_repair_jobs WHERE id=:id", id=records["repair"])
        assert repair["status"] == "work_submitted" and str(repair["ticket_id"]) == records["ticket"]
        delivery = row("SELECT status, order_id, confirmed_at FROM deliveries WHERE id=:id", id=records["delivery"])
        assert delivery["status"] == "confirmed" and delivery["confirmed_at"]
        assert str(delivery["order_id"]) == records["order"]
        serials = connection.execute(text("SELECT serial_number, status FROM equipment_serials WHERE order_id=:id"), {"id": records["order"]}).all()
        assert sorted(s[0] for s in serials) == sorted(records["serials"])
        assert all(s[1] == "installed" for s in serials)
        assert row("SELECT count(*) AS n FROM serial_warranties WHERE order_id=:id AND status='active'", id=records["order"])["n"] == 7
        assert row("SELECT count(*) AS n FROM provider_payment_orders")["n"] == 0
        assert row("SELECT count(*) AS n FROM (SELECT component_code, location_code FROM stock_ledger GROUP BY component_code, location_code HAVING sum(quantity_delta)<0) AS negative_stock")["n"] == 0
        assert row("SELECT count(*) AS n FROM stock_reservations WHERE order_id=:id AND status!='consumed'", id=records["order"])["n"] == 0
    engine.dispose()
    (root / "var/browser-ci/database-verification.json").write_text(json.dumps({"status": "PASS", "records": records}, indent=2))
    print("Independent PostgreSQL persistence oracle PASS")


if __name__ == "__main__":
    main()
