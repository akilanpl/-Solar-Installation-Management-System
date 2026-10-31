"""Verify portable-cluster schemas and prove pytest preserves demo data."""

import argparse
import hashlib
import json

import psycopg
from alembic.config import Config
from alembic.script import ScriptDirectory

from local_postgres import ROOT, connect, load_config

SNAPSHOT = ROOT / "var" / "demo-snapshot.json"
TABLES = {
    "roles",
    "users",
    "customer_profiles",
    "employee_profiles",
    "sessions",
    "email_verification_challenges",
    "customer_sites",
    "enquiries",
    "enquiry_status_history",
    "enquiry_counters",
    "solar_packages",
    "audit_events",
    "alembic_version",
}


def fingerprint(db) -> str:
    rows = []
    for query in (
        "SELECT id, email, role_code FROM users ORDER BY id",
        "SELECT id, reference, status, customer_user_id, site_id FROM enquiries ORDER BY id",
        "SELECT id, enquiry_id, from_status, to_status FROM enquiry_status_history ORDER BY id",
    ):
        rows.append(db.execute(query).fetchall())
    return hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["record", "verify"])
    action = parser.parse_args().action
    config = load_config()
    migrations = ScriptDirectory.from_config(Config(str(ROOT / "apps/api/alembic.ini")))
    # Development deliberately stays at its historical revision until an
    # explicitly authorized development upgrade. Only test must match head.
    for role, database in (("dev", "solarops_dev"), ("test", "solarops_test")):
        with connect(config, database, role) as db:
            tables = {
                row[0]
                for row in db.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            }
            assert TABLES <= tables
            revision = db.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            if role == "test":
                assert revision in migrations.get_heads()
            else:
                assert migrations.get_revision(revision) is not None
            counts = dict(
                db.execute(
                    "SELECT contype, count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace GROUP BY contype"
                ).fetchall()
            )
            assert counts.get("f", 0) >= 10 and counts.get("c", 0) >= 5 and counts.get("u", 0) >= 5
            indexes = db.execute(
                "SELECT count(*) FROM pg_indexes WHERE schemaname='public'"
            ).fetchone()[0]
            print(
                f"{database}: {len(tables)} tables, revision {revision}, {indexes} indexes; FK/check/unique constraints verified."
            )
    try:
        with connect(config, "solarops_dev", "test"):
            raise AssertionError("Test role unexpectedly connected to development database")
    except psycopg.OperationalError as error:
        if "permission denied for database" not in str(error):
            raise
        print("Isolation verified: test role cannot CONNECT to solarops_dev.")
    with connect(config, "solarops_dev", "dev") as db:
        digest = fingerprint(db)
        counts = db.execute(
            "SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM enquiries), (SELECT count(*) FROM enquiry_status_history)"
        ).fetchone()
        if action == "record":
            SNAPSHOT.write_text(
                json.dumps({"fingerprint": digest, "counts": counts}) + "\n", encoding="utf-8"
            )
            print(
                f"Recorded development snapshot: {counts[0]} users, {counts[1]} enquiries, {counts[2]} history rows."
            )
        else:
            original = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
            assert digest == original["fingerprint"], (
                "Development demo data changed during integration testing"
            )
            print(
                "Development accounts, enquiries and history are unchanged after test schema reset."
            )


if __name__ == "__main__":
    main()
