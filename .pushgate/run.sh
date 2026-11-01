#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
: "${SOLAROPS_TEST_DATABASE_URL:?Explicit disposable test database required}"
if [[ -x apps/api/.venv/bin/python ]]; then
  exec apps/api/.venv/bin/python .pushgate/run.py "$@"
elif [[ -x apps/api/.venv/Scripts/python.exe ]]; then
  exec apps/api/.venv/Scripts/python.exe .pushgate/run.py "$@"
else
  echo "pushgate: run uv sync --frozen in apps/api first" >&2
  exit 1
fi
