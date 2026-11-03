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

## Independent final sign-off — current execution

Tested release candidate: `aee6c9be26162927b8dea3275e440968b1920b93`, branch `completion/solarops-20261102`. The checkout was clean at baseline. Both actual listener working directories resolve to this checkout's apps/api and apps/web; HTTP header, BUILD_ID and Git SHA matched before verification. Local API, proxy readiness and frontend returned HTTP 200. Final documentation/QA-runner commit and any rebuilt identity are recorded separately in the delivered manifest. No product features, payment constraints, schema or UI were changed during this sign-off.

**Recommendation: DO NOT SIGN OFF.** Fresh independent non-browser checks pass, but a fresh complete browser lifecycle on this exact candidate has not executed. Prior manual lifecycle/screenshots and 42 axe scans remain historical evidence; they are not newly executed sign-off evidence.

| Acceptance area | Current status | Evidence / limit |
|---|---|---|
|Internal product functionality|PASS within API/DB regression scope|605 fresh backend executions, zero failures; existing linked-state and replay/ownership checks pass. Fresh complete browser functionality remains blocked separately.|
|Browser end-to-end acceptance|BLOCKED|Fresh signup-to-resolution cannot execute: supported local browser control is disabled in Work settings; standalone Chromium fails macOS bootstrap_check_in MachPortRendezvous permission before interaction. No fresh customer or operational success was fabricated.|
|Automated regression testing|PASS for non-browser; BLOCKED for browser|88 frontend tests, typecheck, lint, Ruff, contract regeneration and production build pass; Playwright runner reports three launch failures, not business assertion failures.|
|Accessibility acceptance|NOT TESTED freshly|The prior 42 scans, keyboard evidence and contrast bounds were inspected but not rerun; browser access is blocked. Do not substitute historical scans for fresh acceptance.|
|Razorpay external provider|BLOCKED|All three test configuration settings are absent. Guarded internal simulator remains unchanged; production-denial tests are included in the fresh backend suite. No real provider acceptance claimed.|
|Reliable local demonstration readiness|BLOCKED for final acceptance|HTTP readiness/build identity and seven-role proxy reads pass; existing retained demo may be inspected, but a fresh complete final-source browser replay is missing.|
|Public production readiness|BLOCKED|Internal browser acceptance and provider readiness remain unverified; no deployment, push or merge performed.|

Fresh commands and results:

- `pytest --junitxml=../../var/evidence/signoff-backend.xml`: **605 PASS**, 632.53s, 0 skipped; one Starlette TestClient deprecation warning. Includes maintained release-campaign repeats and a five-minute real HTTP campaign; not this many independent newly authored scenarios.
- `pytest tests/test_release_browser_runner.py`: **2 PASS**; failed/timed-out browser preflight cannot call fixture preparation.
- `npm test`: **88 PASS / 18 files**. `npm run typecheck`, `npm run lint`, `ruff check app tests scripts`: PASS.
- `SOLAROPS_NEXT_DIST_DIR=.next-qa npm run build`: PASS. The first attempt with an output directory outside the app failed module resolution; app-local QA output succeeds. Only that attempt's generated next-env/tsconfig edits were restored; running .next was preserved.
- `export_openapi.py` and `npm run generate:api`, SHA-256 before/after: PASS, committed contracts reproduce source.
- Direct PostgreSQL readback: one test-funded order; completed OTP-verified/customer-acknowledged installation; seven installed serials and active policy-backed warranties; eight zero residual stock balances; closed complaint/resolution v1. This is retained-record integrity, not fresh browser creation.
- Fresh protected logical backup restored into a newly created isolated `solarops_signoff_restore_*` database: **100 tables, all row counts/hashes match**. No existing database overwritten. Backup remains ignored/private.
- HTTP replay/authorization checks: identical outcome replay and intent retry preserve counts, conflicting outcome/duplicate order rejected, missing CSRF rejected, staff access denied to customer, five cross-customer reads denied. No financial amount changed.
- `SOLAROPS_WEB_URL=http://127.0.0.1:3063 npx playwright test --config playwright.complete.config.ts lifecycle-persistence.spec.ts --project chromium`: **BLOCKED**, three browser launch failures before assertions. Installed Playwright 1.64.1/Chromium is present; not a missing-binary or readiness error.
- Installed Brave attempted via normal Playwright launch with Chromium sandbox enabled: aborts before interaction. No OS/browser protections bypassed.

Reproducible isolated browser command:

```sh
apps/api/.venv/bin/python apps/api/scripts/run_release_browser.py --env .env
```

This command validates the explicitly disposable test target, checks QA ports 3001/8001 without stopping existing services, and launches a sandboxed Chromium probe **before** fixture preparation. Only after that succeeds does the maintained runner prepare synthetic accounts and start owned FastAPI/Next servers through `playwright.qa.config.ts`, then request the complete maintained suite. Current observed result: **BLOCKED at browser preflight; database untouched**. The post-preflight complete suite and fresh final-source lifecycle are not claimed executed. The QA config was corrected to accept an explicitly named guarded release test database as well as local solarops_test; it still rejects development/remote targets. Existing assertions are unchanged. Existing suite fixture/contract failures may emerge after the environment is unblocked and must be fixed rather than hidden.

CI alternative assessment: Docker/Podman unavailable. GitHub reports zero self-hosted runners. The two existing hosted workflows run only on push/PR, have no workflow_dispatch, and cannot test this unpublished local SHA without publishing/configuring an exact-source runner. No remote run was triggered, because push/publication is explicitly unauthorized. A run of older remote source would not close this gate.

Required next action: restore supported browser access in Work settings or supply a permitted isolated browser/CI runner for the exact local source. Do not change macOS protections. Then run the command, repair any genuine harness/product failures, and execute a newly generated customer through the entire lifecycle with fresh screenshots/network/DB evidence. Configure authorized Razorpay **test-only** credentials privately for a separate provider campaign. No production credential request is needed.

Evidence: `signoff-source.json`, `signoff-restore.json`, `signoff-backend.xml`, `signoff-runner.xml`, `signoff-playwright.log`, `signoff-browser-alternative.log`, `signoff-single-command.log`, and the current execution manifest. Prior completion statements elsewhere in these reports are superseded by this scoped sign-off section.
