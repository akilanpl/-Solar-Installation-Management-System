"""Restore a private candidate backup into a new owned DB, compare, then clean up."""

import argparse
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

source = "solarops_ultimate_preview_20261031"
target = "solarops_restorecheck_" + uuid.uuid4().hex[:10]
parser = argparse.ArgumentParser()
parser.add_argument("--archive", default="../../var/ultimate-before-serial-custody.dump")
args = parser.parse_args()
archive = Path(args.archive).resolve()
if not archive.is_file():
    raise RuntimeError("Create the named private candidate backup first.")
started = time.monotonic()
subprocess.run(["createdb", target], check=True)
try:
    subprocess.run(
        ["pg_restore", "--exit-on-error", "--dbname=" + target, str(archive)], check=True
    )

    def snapshot(database):
        engine = create_engine("postgresql+psycopg:///" + database)
        try:
            with engine.connect() as conn:
                results = {}
                for table in inspect(conn).get_table_names():
                    rows = sorted(
                        json.dumps(list(row), default=str, sort_keys=True)
                        for row in conn.execute(text('SELECT * FROM "' + table + '"'))
                    )
                    results[table] = {
                        "rows": len(rows),
                        "hash": hashlib.sha256("\n".join(rows).encode()).hexdigest(),
                    }
                return results
        finally:
            engine.dispose()

    before, after = snapshot(source), snapshot(target)
    if before != after:
        raise RuntimeError("Restored rows differ from preserved candidate snapshot.")
    result = {
        "source": source,
        "restore_target": target,
        "all_rows_match": True,
        "tables": len(before),
        "table_counts": {table: value["rows"] for table, value in before.items()},
        "archive_bytes": archive.stat().st_size,
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    Path("../../var/ultimate-restore-evidence.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Restore rehearsal passed: {len(before)} tables match; {result['duration_seconds']} seconds."
    )
finally:
    # This target was created by this invocation; never drop any existing DB.
    subprocess.run(["dropdb", target], check=True)
