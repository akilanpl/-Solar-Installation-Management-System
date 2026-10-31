"""Run only the isolated local candidate, loading values without shell evaluation."""

import argparse
import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument("--migrate", action="store_true")
args = parser.parse_args()
values = dotenv_values(root / "var/ultimate-preview.env", interpolate=False)
os.environ.update({key: value for key, value in values.items() if value is not None})
if make_url(
    os.environ.get("SOLAROPS_DATABASE_URL", "")
).database != "solarops_ultimate_preview_20261031" or os.environ.get("SOLAROPS_APP_ENV") not in {
    "development",
    "test",
}:
    raise RuntimeError(
        "Candidate runner requires the named isolated preview and nonproduction configuration."
    )
os.chdir(root / "apps/api")
if args.migrate:
    subprocess.run(
        [".venv/bin/python", "scripts/verify_candidate_upgrade.py"],
        check=True,
        env={**os.environ, "PYTHONPATH": "."},
    )
else:
    os.execv(
        ".venv/bin/uvicorn", ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8002"]
    )
