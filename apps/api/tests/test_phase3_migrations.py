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
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "e6a2b3c4d5f6"
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
    ):
        assert name in schema.get_table_names()
        assert schema.get_foreign_keys(name)
    assert schema.get_check_constraints("stock_operation_lines")
    assert schema.get_unique_constraints("equipment_serials")
    assert schema.get_indexes("stock_ledger")
    saved = client.get(f"/api/v1/enquiries/{enquiry_id}")
    assert saved.status_code == 200
    assert saved.json()["reference"] == created.json()["reference"]
