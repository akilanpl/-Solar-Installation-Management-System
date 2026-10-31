# Local preview and future release runbook

Status: PARTIAL. Integration preview exists; fresh merged-main release does not.

Checkout: `/Users/akilan/Downloads/SOLOPS-integration`, branch `integration/final-release`. `~/Downloads/SOLOPS-final` was not created because main was not merged or verified as released. Never label this preview as the final-main product.

PostgreSQL 15.19 existing local server on 5432 is reused, with separate NEW databases:

- `solarops_release_test_20261031`: disposable destructive tests only; explicit exact-name opt-in.
- `solarops_release_demo_20261031`: preview database; migration head e6a2b3c4d5f6; six development-only staff, zero customer enquiries at verification. No fabricated completed orders, payments or physical movements seeded.

Existing solarops/solarops_test were untouched. These preview databases share the local OS database role; they are not independent-role production isolation. No existing development schema was migrated or backed up because none was changed.

Private, ignored configuration: `var/release-preview.env` (mode 0600). Generated development staff password is in `var/dev-seed-password.txt`; it is not included in reports. Use employee ID EMP-SALES-001 / EMP-TECH-001 / EMP-ADMIN-001 / EMP-WH-001 / EMP-WHM-001 / EMP-SUP-001 with that local generated password. Public customers must sign up and verify using the explicitly local mailbox button. Do not reuse development accounts outside this preview.

Start backend in one terminal:

```sh
cd /Users/akilan/Downloads/SOLOPS-integration/apps/api
set -a
source ../../var/release-preview.env
set +a
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Start frontend in another terminal:

```sh
cd /Users/akilan/Downloads/SOLOPS-integration/apps/web
WATCHPACK_POLLING=true SOLAROPS_API_ORIGIN=http://127.0.0.1:8001 SOLAROPS_NEXT_DIST_DIR=.next-release-preview NEXT_PUBLIC_SOLAROPS_ENV=development NEXT_TELEMETRY_DISABLED=1 node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3001
```

Polling avoids this sandbox's file-watcher limit. Do not run npm ci while a frontend process uses node_modules; stop it first, install, then restart. Next may add its preview dist types to tsconfig while starting development.

Verified URLs at final checkpoint:

- http://127.0.0.1:3001/login — actual Next login page loaded by app browser.
- http://127.0.0.1:3001/api/v1/ready — actual same-origin proxy returns ready/database up.
- http://127.0.0.1:8001/api/v1/ready — FastAPI returns ready/database up.
- http://127.0.0.1:8001/docs — FastAPI documented routes; no full browser acceptance claimed.

Listeners at verification: frontend PID 62850, backend PID 64766. Stop with Ctrl+C in their terminal, or recheck `lsof -nP -iTCP:3001 -iTCP:8001 -sTCP:LISTEN` and then send SIGTERM only to the verified preview PIDs (`kill 62850 64766` while these are still the same processes). Do not stop the existing PostgreSQL service; it may host other development work. The preview was running when verified, not a guarantee of future process lifetime.

Reinstall dependencies when needed: `UV_CACHE_DIR=/private/tmp/solarops-uv-cache uv sync --frozen` from apps/api and `npm ci --cache /private/tmp/solarops-npm-cache` from apps/web. Apply migrations only after verifying the private preview URL names the intended NEW database. Seed only with guarded `scripts/seed_release_preview.py` in development.

Future final release: finish all mandatory gaps; pass full gate/real browser acceptance; fetch latest remote main; push integration and open PR; verify exact-head CI/reviews; merge through permitted GitHub method; fetch and verify remote merge SHA; then clone main into a nonexisting final directory, verify HEAD equals merge SHA and create another separate demo database. No step in this future sequence has been represented as completed.

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
