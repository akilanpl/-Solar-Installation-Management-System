# Security and reliability

Status: PARTIAL.

Verified safeguards exercised locally: customer-only public signup, Argon2id, server sessions and role/ownership boundaries, CSRF, email verification tests, installation OTP lockout/expiry/replay/concurrency, inactive technician rejection, arrival requirement, authenticated customer acknowledgment, file type/size/hash/custody checks, Secure-cookie/HTTPS configuration rejection and explicit trusted-proxy handling.

Request IDs are generated server-side, returned as X-Request-ID and attached to logging extra fields. A JSON log formatter/collector is not configured; do not claim distributed observability. Database exception messages no longer print SQL parameter values into operational logs. Process-local throttling remains unsuitable for horizontal scale. Proxy trust defaults to empty; behind Next.js this can group users under a loopback address until a sanitizing trusted ingress is configured.

Data scope: existing `solarops` and `solarops_test` databases were not reset, migrated or seeded. Tests use newly created `solarops_release_test_20261031`, with explicit opt-in guard. Preview uses newly created `solarops_release_demo_20261031`. A separate cluster init failed due sandbox shared-memory denial, so both new databases use the existing PostgreSQL 15.19 server. They are separate databases, not separate database roles or servers. This is local acceptance only.

Before any existing development/staging schema upgrade: take pg_dump custom-format backup to protected storage, record source migration SHA and row counts, verify pg_restore into a separately named database, validate application reads and totals, then apply additive migration. This procedure is documented but no real existing-data restore rehearsal was executed. No database dump was committed.

New migration: e6a2b3c4d5f6. Empty disposable upgrade and previous-phase downgrade/upgrade tests pass in pytest. Downgrading drops installation upload metadata; back up DB and evidence together and prefer forward repair. Never downgrade the existing development database as an acceptance test.

Storage limitations: bounded images and dimensions, generated names and SHA checks protect upload/download. A transaction failure after file write can leave an orphan; an audited retention/cleanup job and object-store/DB consistent backups remain required. Hash/HMAC protection is not protection against an attacker holding both database and server key. No independent security penetration test, secret-history scan, coverage/mutation campaign or load/resilience campaign was completed.

Dependency evidence: npm audit initially 2 critical/1 high; targeted Vitest 4.1.12 and PostCSS 8.5.23 (including Next override) remove high/critical. 18 moderate findings remain; zero high/critical. Python pip-audit inspected 44 installed packages and reported no known vulnerabilities. A current tracked-file detect-secrets scan produced 35 candidates in 20 files, classified as examples/test fixtures/migration IDs and password-validation keywords; no live credential found. It did not scan every historical outgoing commit. No staging/production deployment was performed.

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
