# Fresh browser acceptance handoff

This is verification infrastructure only. Application behavior, schema and credentials are unchanged.

## Execution

Workflow: `.github/workflows/browser-acceptance.yml` (**Fresh browser acceptance**).
Branch to push, only after authorization: `completion/solarops-20261102`.
A push to that exact branch triggers the workflow, including its first run; manual dispatch is also declared. No push or workflow dispatch was performed while preparing this change.

The job checks out the triggering SHA, records it in `source-sha.txt`, installs frozen Python/npm dependencies and Playwright Chromium on Ubuntu 24.04, creates a job-owned PostgreSQL 16 service, migrates an empty database and provisions only six staff accounts. It builds Next.js, then Playwright starts FastAPI on 8001 and the built Next.js server on 3001. Both servers prohibit reuse. No existing demo fixtures, customer credentials, SQL business-state injection or mocked routes are used.

The bootstrap accepts only a loopback database named `solarops_browser_ci` (or a 12-hex suffixed local instance), explicitly matched by `SOLAROPS_BROWSER_DATABASE_NAME`, in development mode. It refuses nonempty databases and external payment/email providers. It never drops a schema. Ephemeral staff/session secrets are generated and masked per job. Synthetic email and evidence stay private to the job. No GitHub secrets are required.

The independently executable entry points, after installing dependencies and supplying the environment declared in the workflow, are:

```sh
# Repository root; database must already exist and be empty.
mkdir -p var/browser-ci/private
(cd apps/api && uv run python scripts/prepare_browser_ci.py)
(cd apps/web && npm run build)
(cd apps/web && npm run e2e -- --config playwright.ci.config.ts)
(cd apps/api && uv run python scripts/verify_browser_ci.py)
```

## Acceptance contract

One sequential fresh campaign preserves the relationship among all records:

- Customer signs up, verifies captured development email and logs in through actual browser UI.
- Authorized staff HTTP operations qualify the enquiry, assign/perform an evidenced survey, approve it and issue a quotation. The customer accepts the actual version in the browser.
- A clearly test-only internal payment simulation funds the order. No cash receipt or provider settlement is fabricated. Duplicate confirmation and picking without stock must fail.
- Validated synthetic stock receipts establish serial custody; all seven tracked units are assigned and actual location stock allocated. Dispatch, delivery and confirmation precede installation.
- Declared technician availability permits a real appointment. Completion before OTP and before acknowledgment must fail. Uploaded synthetic evidence, readings and actual nonfuture work timestamps form the work summary; the customer reviews all seven identities and acknowledges it through UI. Completion activates seven configured unit warranties.
- The customer sees equipment and raises the complaint through UI. Support triages/assigns it; the assigned technician records diagnostics, work, uploaded evidence and a submitted summary through authenticated HTTP. The customer accepts the versioned repair summary through UI before support closes it.
- A separate browser context logs in again and verifies closed-ticket/completed-job/warranty persistence. A second fresh customer cannot retrieve the first customer's order, job, complaint or coverage. Customer, warehouse, sales and support authorization boundaries and missing CSRF are asserted.
- Axe checks fail on serious/critical WCAG A/AA violations on critical customer and staff pages. Screenshots and horizontal overflow checks cover 390/768/1280 widths; keyboard focus must leave the document body. Runtime page errors, unexpected HTTP 5xx, failed network requests and application console errors fail the test.
- A separate read-only PostgreSQL oracle verifies saved cross-record identity, completed signed work, installed serials, active warranties, consumed reservations, closed complaint and test-only payment provenance. Provider payment rows must remain absent.

No retries, skipped lifecycle steps, expected failures or continue-on-error settings hide defects. A genuine assertion failure stops acceptance and preserves evidence. This suite covers the stated critical campaign, not the older all-page audit or every possible business permutation.

## Evidence and provider boundary

Every run retains its source SHA, migration/build/API/Next/PostgreSQL logs, HTML/JUnit/JSON reports, screenshot/axe attachments, full primary/staff traces and failure video for 14 days. The private mailbox, uploaded fixture files, environment and database credentials are excluded from the artifact allowlist. Traces contain ephemeral fixture authentication and must be treated as test evidence.

Razorpay provider testing remains **BLOCKED until legitimate test credentials exist** and must run separately. This job explicitly asserts that provider capability is disabled and creates no provider payment records. Passing its internal simulation does not establish provider readiness.

## Local validation of this infrastructure

- `actionlint` 1.7.7: workflow passes.
- Fresh local disposable PostgreSQL: migrations pass; 100 tables, six staff, zero customers/orders after bootstrap. Real FastAPI readiness and seeded staff login pass; Razorpay capability disabled. A second bootstrap refuses the nonempty database.
- Independent persistence SQL: all queries successfully planned against the migrated schema. Full final-state oracle is NOT RUN until the browser campaign produces records.
- Frontend production build passes; Playwright discovers exactly one fresh campaign without launching a browser.
- Frontend regression: 88 tests across 18 files pass; ESLint and TypeScript pass.
- Runner/target safety regression: 15 tests pass; Python Ruff checks pass.

The desktop built-in browser is already confirmed disabled in Work settings. Earlier Chromium logs show macOS Mach-port permission failure before navigation; the alternative browser also aborted. These unavailable environments were not retried or bypassed. Hosted browser execution is **NOT RUN**. These local checks do not establish browser acceptance or release sign-off.
