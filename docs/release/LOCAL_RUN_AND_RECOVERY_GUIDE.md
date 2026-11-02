# Local Run And Recovery Guide

Lifecycle follow-up, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`; baseline handoff `2b892fe3ec450ca1121afaaabdb1941d3f8716b9`. Final source/build SHA and post-commit smoke are in the delivered `FINAL_EXECUTION_MANIFEST.json`. Previous test counts are historical, not substituted for this run.

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

Interactive demo: sign in as the primary fixture; open ENQ-2026-000005 and accepted QTN-2026-000001 v1. Sign in separately as EMP-SALES-001 to review the same qualified enquiry, approved SUR-2026-000001 and BOM. EMP-TECH-001 sees that exact survey and uploaded labelled synthetic evidence. Warehouse staff/manager, support and admin have their actual empty/zero operational states. Return to customer Payments: external provider remains blocked, but the internal test-only receipt and completed fixture order are persisted. My equipment shows the seven actual test serial-policy records and Complaints shows the closed case. Do not enter fictitious cash or confirm physical events to make the demo appear complete. Repeated logins can legitimately trigger abuse limits; wait for expiry or restart only this isolated owned development process before a clean seven-account run.

Recovery: protect `var/completion-private.dump` and the private .env/credentials; the fresh restore rehearsal matched 100 tables. Restore only into a newly created isolated database, compare row snapshots, then point a stopped candidate at that database after review. Never overwrite another database or apply destructive downgrades. The existing demo/test/restore databases were retained for reproducibility. Missing Razorpay test credentials belong in ignored local configuration, never in chat or Git.

Final source/build identity, readiness and current running status are in the delivered execution manifest; the URL alone is not proof of a complete funded business journey.


## Follow-up lifecycle demo and audit

The completed fixture is retained; do not recreate cash/stock events to demonstrate it. Customer can read ORD-2026-000001, completed JOB-2026-000001, seven serial warranties and closed TKT-2026-000001. Technician RPJ-2026-000001 remains a submitted repair work record; ticket closure is separate and customer-confirmed. Finance intentionally shows the order as unreconciled for actual valuation/revenue because no actual money/cost evidence was invented.

The development payment interface appears only with the existing public development build flag AND authenticated backend capability. It creates a pending intent, requires an explicit outcome and no-money acknowledgment, retains idempotency on retry, and uses normal server constraints. Production rejects simulation regardless of a misconfigured frontend flag. Do not use the cash-receipt form to invent settlement.

For opt-in local axe audits only:

```sh
SOLAROPS_LOCAL_AUDIT=on apps/api/.venv/bin/python apps/api/scripts/complete_local.py serve --env .env --api-port 8063 --web-port 3063
# Open /api/dev/a11y?path=/customer/payments&width=390 while signed in.
# Click Run accessibility audit. This is a read-only QA document, not a product workflow.
```

Without the explicit flag, or with production APP_ENV/non-loopback host, the audit endpoint returns 404. Final normal startup leaves it disabled. Rebuild only after stopping the owned launcher; restart now tolerates TIME_WAIT while still refusing active listeners. Run `npm run e2e -- --config playwright.complete.config.ts lifecycle-persistence.spec.ts` only against the isolated completed fixture or prepare a fresh documented campaign. Standalone Chromium launch is currently blocked by macOS, not repaired by disabling security.
