#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
: "${SOLAROPS_TEST_DATABASE_URL:?Explicit disposable test database required}"
exec python3 .pushgate/run.py "$@"
