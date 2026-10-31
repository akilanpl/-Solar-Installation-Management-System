"""Migration proof against the disposable database, preserving Phase 1 records."""

import uuid

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from app.db.base import Base
from app.models.enquiry import Enquiry
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from tests.conftest import TEST_DATABASE_URL, _assert_safe
from tests.test_enquiries import ENQUIRY, _customer_headers

pytestmark = pytest.mark.database


def test_migrated_schema_matches_current_sqlalchemy_metadata(application):
    _assert_safe(TEST_DATABASE_URL)
    with application.state.engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []


def test_phase3_round_trip_keeps_existing_phase1_record(client, application):
    _assert_safe(TEST_DATABASE_URL)
    created = client.post(
        "/api/v1/enquiries",
        json=ENQUIRY,
        headers={
            **_customer_headers(client, application),
            "Idempotency-Key": "qa-migration-record",
        },
    )
    assert created.status_code == 201
    enquiry_id = uuid.UUID(created.json()["id"])
    config = Config("alembic.ini")
    command.downgrade(config, "c4e8a1b27d90")
    try:
        assert "stock_ledger" not in inspect(application.state.engine).get_table_names()
        with Session(application.state.engine) as db:
            assert db.get(Enquiry, enquiry_id).reference == created.json()["reference"]
    finally:
        _assert_safe(TEST_DATABASE_URL)
        command.upgrade(config, "head")
    with application.state.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "4b1c2d3e4f51"
    schema = inspect(application.state.engine)
    for name in (
        "stock_ledger",
        "stock_operations",
        "stock_reservations",
        "equipment_serials",
        "deliveries",
        "installation_jobs",
        "installation_otps",
        "warranties",
        "service_tickets",
        "service_ticket_events",
        "ticket_repair_jobs",
        "service_ticket_attachments",
        "resolution_acknowledgments",
        "warranty_policies",
        "warranty_policy_versions",
        "serialized_asset_coverage",
        "coverage_decisions",
        "warranty_exceptions",
        "service_price_books",
        "service_tax_policies",
        "service_estimates",
        "estimate_decisions",
        "service_invoices",
        "service_credit_notes",
        "replacement_decisions",
        "return_inspections",
    ):
        assert name in schema.get_table_names()
        assert schema.get_foreign_keys(name)
    assert schema.get_check_constraints("stock_operation_lines")
    assert schema.get_unique_constraints("equipment_serials")
    assert schema.get_indexes("stock_ledger")
    saved = client.get(f"/api/v1/enquiries/{enquiry_id}")
    assert saved.status_code == 200
    assert saved.json()["reference"] == created.json()["reference"]


def test_forward_hardening_migration_preserves_financial_and_ledger_records(client, application):
    """Upgrade a representative older Phase 3 dataset, not merely an empty DB."""
    import hashlib
    import json

    from tests.test_phase3_warehouse_installation import (
        _all_staff,
        _confirmed_order,
        _receipt_validate,
        _warehouse,
    )

    _assert_safe(TEST_DATABASE_URL)
    _all_staff(application)
    _confirmed_order(client, application, email="preserved-financial-fixture@example.com")
    _receipt_validate(client, _warehouse(client), "PANEL-550", "3")
    tables = [
        "quotations",
        "quotation_lines",
        "quotation_acceptances",
        "payment_intents",
        "payment_attempts",
        "sales_orders",
        "sales_order_lines",
        "stock_operations",
        "stock_operation_lines",
        "stock_ledger",
        "audit_events",
        "surveys",
    ]

    def snapshot():
        with application.state.engine.connect() as conn:
            conn.execute(text("SET TIME ZONE 'UTC'"))
            result = {}
            for table in tables:
                rows = sorted(
                    json.dumps(list(row), default=str, sort_keys=True)
                    for row in conn.execute(text("SELECT * FROM " + table))
                )
                assert rows, table + " fixture must contain representative preserved records"
                result[table] = (len(rows), hashlib.sha256("\n".join(rows).encode()).hexdigest())
            return result

    original = snapshot()
    config = Config("alembic.ini")
    command.downgrade(config, "e6a2b3c4d5f6")
    try:
        assert snapshot() == original
        assert "provider_events" not in inspect(application.state.engine).get_table_names()
    finally:
        _assert_safe(TEST_DATABASE_URL)
        command.upgrade(config, "head")
    assert snapshot() == original
