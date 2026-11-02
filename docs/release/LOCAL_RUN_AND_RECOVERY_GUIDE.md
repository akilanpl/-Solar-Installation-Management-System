# Local Run And Recovery Guide

Current completion audit, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`, integrated base `2f6e7122494ce214036d9baf98128411bdbea3c5`. Final commit/build identity and post-commit smoke are recorded in the delivered `FINAL_EXECUTION_MANIFEST.json`. Historical reports describe earlier candidates and are not current evidence.

Checkout: this chat workspace `work/SolarOps`, branch `completion/solarops-20261102`. Use Python 3.12, locked uv environment, Node/npm and PostgreSQL 15+. Existing PostgreSQL on localhost:5432 stays running. Ports 3061/3062/8061/8062 belong to earlier services and were preserved. This candidate uses **http://127.0.0.1:3063/login** and API http://127.0.0.1:8063/api/v1/ready.

From repository root:

```sh
UV_CACHE_DIR=/private/tmp/solarops-uv-cache uv sync --project apps/api --frozen --group dev
npm --prefix apps/web ci --cache /private/tmp/solarops-npm-cache --no-audit --no-fund
# Keep private .env and apps/web/.env.local; never print/source them into logs.
# .env.local contains only NEXT_PUBLIC_SOLAROPS_ENV=development.
apps/api/.venv/bin/python apps/api/scripts/complete_local.py migrate --env .env
npm --prefix apps/web run build
apps/api/.venv/bin/python apps/api/scripts/complete_local.py serve --env .env --api-port 8063 --web-port 3063
```

The launcher waits for API and frontend HTTP readiness. Ctrl-C stops only its own children. It refuses occupied ports; inspect ownership instead of terminating another service. Update private trusted origins if deliberately selecting a different web port. Stop the owned frontend before replacing its production build, then restart. A seed rerun uses existing credentials/records; it does not create funded orders or install equipment.

Test isolation: read `.env` with `dotenv_values(..., interpolate=False)` and pass values as a subprocess environment, including both `SOLAROPS_TEST_DATABASE_URL` and `SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME`. Never point pytest at the demo DB. Test role CREATEDB is needed only for the disposable restore campaign; revoke it afterward.

Development credentials stay in owner-only ignored `var/dev-seed-password.txt` (staff), `var/demo-credentials.json` (demo customers), `var/completion-customer.json` (the browser-created primary fixture). No credentials are delivered publicly.

Reproducible read-only multi-role demo:

```sh
apps/api/.venv/bin/python apps/api/scripts/demonstrate_local.py --url http://127.0.0.1:3063
```

Interactive demo: sign in as the primary fixture; open ENQ-2026-000005 and accepted QTN-2026-000001 v1. Sign in separately as EMP-SALES-001 to review the same qualified enquiry, approved SUR-2026-000001 and BOM. EMP-TECH-001 sees that exact survey and uploaded labelled synthetic evidence. Warehouse staff/manager, support and admin have their actual empty/zero operational states. Return to customer Payments: provider blocked, no receipts. Do not enter fictitious cash or confirm physical events to make the demo appear complete. Repeated logins can legitimately trigger abuse limits; wait for expiry or restart only this isolated owned development process before a clean seven-account run.

Recovery: protect `var/completion-private.dump` and the private .env/credentials; the fresh restore rehearsal matched 100 tables. Restore only into a newly created isolated database, compare row snapshots, then point a stopped candidate at that database after review. Never overwrite another database or apply destructive downgrades. The existing demo/test/restore databases were retained for reproducibility. Missing Razorpay test credentials belong in ignored local configuration, never in chat or Git.

Final source/build identity, readiness and current running status are in the delivered execution manifest; the URL alone is not proof of a complete funded business journey.
