"""Preserve every original row while upgrading only the restored candidate DB."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import app.models  # noqa: F401
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.base import Base
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

url = os.environ["SOLAROPS_DATABASE_URL"]
if make_url(url).database != "solarops_ultimate_preview_20261031":
    raise RuntimeError("Only the explicitly restored candidate database is permitted.")
engine = create_engine(url)
before = {}
with engine.connect() as conn:
    schema = inspect(conn)
    for table in schema.get_table_names():
        if table == "alembic_version":
            continue
        columns = [column["name"] for column in schema.get_columns(table)]
        query = "SELECT " + ",".join('"' + c + '"' for c in columns) + ' FROM "' + table + '"'
        rows = sorted(
            json.dumps(list(row), default=str, sort_keys=True) for row in conn.execute(text(query))
        )
        before[table] = (query, rows)
subprocess.run([".venv/bin/alembic", "upgrade", "head"], check=True)
results = []
with engine.connect() as conn:
    for table, (query, rows) in before.items():
        after = sorted(
            json.dumps(list(row), default=str, sort_keys=True) for row in conn.execute(text(query))
        )
        preserved = (
            all(row in after for row in rows) if table == "warehouse_locations" else rows == after
        )
        if not preserved:
            raise RuntimeError("Preserved records changed in " + table)
        results.append(
            {
                "table": table,
                "before_count": len(rows),
                "after_count": len(after),
                "existing_rows_preserved": True,
                "original_columns_sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest(),
            }
        )
    differences = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    if differences:
        raise RuntimeError("ORM schema differences: " + repr(differences))
    head = conn.scalar(text("SELECT version_num FROM alembic_version"))
Path("../../var/ultimate-upgrade-evidence.json").write_text(
    json.dumps(
        {
            "database": "solarops_ultimate_preview_20261031",
            "head": head,
            "metadata_matches": True,
            "tables": results,
        },
        indent=2,
    )
    + "\n"
)
print(f"{len(results)} existing tables preserved; ORM metadata matches; head {head}")
engine.dispose()
