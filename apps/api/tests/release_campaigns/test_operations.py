"""Actual logical backup/restore rehearsal of a disposable seeded PostgreSQL DB."""

import hashlib
import json
import os
import shutil
import subprocess
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from tests.conftest import TEST_DATABASE_URL, _assert_safe
from tests.test_phase3_warehouse_installation import _confirmed_order
from tests.test_phase4c_finance import admin_login, foundation, invoice

pytestmark = pytest.mark.database


def _snapshot(engine):
    result = {}
    with engine.connect() as conn:
        conn.execute(text("SET TIME ZONE 'UTC'"))
        for table in sorted(inspect(conn).get_table_names(schema="public")):
            # Names are server-discovered identifiers, quoted by the dialect.
            name = conn.dialect.identifier_preparer.quote(table)
            rows = sorted(
                json.dumps(row[0], sort_keys=True, separators=(",", ":"))
                for row in conn.execute(text(f"SELECT to_jsonb(t) FROM {name} AS t"))
            )
            result[table] = (len(rows), hashlib.sha256("\n".join(rows).encode()).hexdigest())
    return result


def test_disposable_backup_restores_every_table_and_preserves_financial_rows(
    client, application, tmp_path
):
    _assert_safe(TEST_DATABASE_URL)
    source = make_url(TEST_DATABASE_URL)
    assert source.host in {"127.0.0.1", "localhost"}, (
        "backup rehearsal requires isolated local PostgreSQL"
    )
    for binary in ("pg_dump", "pg_restore", "createdb", "dropdb"):
        assert shutil.which(binary), f"Missing required backup prerequisite: {binary}"
    _, _, _, policy = foundation(client, application)
    order = _confirmed_order(client, application)
    invoice(client, admin_login(client), policy, order)
    before = _snapshot(application.state.engine)
    for table in (
        "sales_orders",
        "finance_records",
        "finance_entries",
        "finance_lines",
        "audit_events",
    ):
        assert before[table][0] > 0, f"Representative business fixture missing from {table}"
    environment = os.environ.copy()
    environment.update(
        PGHOST=source.host,
        PGPORT=str(source.port or 5432),
        PGUSER=source.username or "",
        PGPASSWORD=source.password or "",
    )
    backup = tmp_path / "disposable.dump"
    subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--file",
            str(backup),
            "--dbname",
            source.database,
        ],
        env=environment,
        check=True,
        capture_output=True,
        timeout=120,
    )
    assert backup.stat().st_size > 0
    restored_name = "solarops_release_restore_" + uuid.uuid4().hex
    # Use the local OS owner for CREATEDB only; application role owns/restores
    # this uniquely named test database. Never drop the input database.
    owner_environment = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    restored = None
    created = False
    try:
        subprocess.run(
            ["createdb", "--owner", source.username, restored_name],
            env=owner_environment,
            check=True,
            capture_output=True,
            timeout=30,
        )
        created = True
        subprocess.run(
            [
                "pg_restore",
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "--dbname",
                restored_name,
                str(backup),
            ],
            env=environment,
            check=True,
            capture_output=True,
            timeout=120,
        )
        restored = create_engine(source.set(database=restored_name))
        assert _snapshot(restored) == before
        # A functioning restored readiness query and intact FK enforcement.
        with restored.connect() as conn:
            assert conn.scalar(text("SELECT 1")) == 1
            assert conn.scalar(text("SELECT count(*) FROM pg_constraint WHERE contype='f'")) > 0
    finally:
        if restored is not None:
            restored.dispose()
        if created:
            assert restored_name.startswith("solarops_release_restore_")
            subprocess.run(
                ["dropdb", restored_name],
                env=owner_environment,
                check=True,
                capture_output=True,
                timeout=30,
            )
