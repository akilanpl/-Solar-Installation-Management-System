# Backend acceptance

Status: PARTIAL. Baseline reproduced: 122 passed. Hardened checkpoint: 147 passed, zero failures, one Starlette/httpx deprecation warning. Final gate run completed the backend suite in 35.74 seconds. Python 3.12.13; PostgreSQL 15.19; frozen uv lock installed. Existing development databases were not used for destructive tests.

All migrations from empty, metadata parity and the Phase 3 downgrade/upgrade round trip retaining an enquiry are covered by the suite. Current single head: e6a2b3c4d5f6. Preview database current revision independently queried as e6a2b3c4d5f6. This is not a representative full development-data migration or restore rehearsal.

New regressions cover: secret-free staff job responses; keyed job/purpose-bound OTP; isolated security transaction preserving unrelated caller rollback; simultaneous consumption once; malformed/truncated/wrong-format/oversize image rejection; upload metadata/time/hash/custody; customer ownership on downloads; arbitrary and cross-job photo rejection; capacity/time/electrical validation; technician cannot acknowledge for customer; stale summary/replay/signature mutation protection; modified-file rejection; authenticated code reissue/revocation; insecure production config rejection; untrusted forwarding-header rejection.

Existing independent QA lockout, inactive technician and arrival regressions remain. Positive old installation tests now upload valid fixture images, obtain code through test email capture and authenticate the owning customer for acceptance. These tests represent isolated sandbox/physical fixtures, not real delivered equipment or bank verification.

Remaining mandatory backend coverage/implementation gaps: multi-location allocation and location-aware reservations, partial deliveries/remaining quantities, inspected returns, full purchase approval/receipt chain, all scheduling skill/hour/overlap rules, product-specific serialized warranties, installed BOM/capacity/serial confirmation, provider adapter/webhook/refunds and stronger load/recovery coverage. The existing 147 passes do not verify these missing requirements.

OpenAPI generation is byte-reproducible at this checkpoint: SHA256 12c6babc3ca7466d7a7e71a6c3beb28dade1accd8d02736aa212f1a9baf8d8e4. Python pip-audit checked 44 packages and returned no known vulnerabilities; this is not a guarantee of absence of vulnerabilities.

## Executed checkpoint evidence

Tested code SHA: `ffae1ecf63d8d99b71f6a3d02ee6f531e275c253` (later report commits change documentation only). Baseline 122 backend tests; hardened 147 backend tests and 7 frontend tests. Commands are cwd-sensitive:

```sh
# From apps/api:
SOLAROPS_TEST_DATABASE_URL=postgresql+psycopg:///solarops_release_test_20261031 SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=solarops_release_test_20261031 .venv/bin/pytest
.venv/bin/ruff check app tests scripts
# With the private preview config loaded, read-only migration verification:
.venv/bin/alembic heads
.venv/bin/alembic current
# Generate API contracts under explicitly configured local/test settings:
.venv/bin/python scripts/export_openapi.py
# From apps/web:
npm ci --cache /private/tmp/solarops-npm-cache
npm test
npm run typecheck
npm run lint
npm run generate:api
npm run build
npm audit --audit-level=high --json
# From repository root:
SOLAROPS_TEST_DATABASE_URL=postgresql+psycopg:///solarops_release_test_20261031 SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=solarops_release_test_20261031 .pushgate/run.sh
```

Result: all available executed gate stages pass; aggregate remains INCOMPLETE 55.4/100 because ten required campaign entries are not run. Migration head e6a2b3c4d5f6. Two attempted browser tests failed at Chromium launch due sandbox permission, zero browser passes. Final npm audit 18 moderate/zero high/critical; Python audit 44 packages/zero known findings. Frozen dependency sync, contract regeneration and production build executed. Complete browser/operational requirements, coverage/mutation/load/restore and exact-head GitHub CI are not verified.

Historical QA CI success: https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41193327252. Latest unrelated frontend CI: https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41195733652; source inspection found success-printing lint/generator scripts, so its green result is not lint/contract evidence. No CI URL exists for the unpushed integration commit. Remote main remains a95533838fd4413233ed69edf2ce671260ea8c3a.
