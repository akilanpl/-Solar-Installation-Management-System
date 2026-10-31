# SolarOps frontend QA report

Date: 2026-10-31 (Asia/Calcutta). Repository: `akilanpl/-Solar-Installation-Management-System`. Branch: `test/qa-integration`. Tested source: **`c83bd1150d07e26e9fc8769cc7ea52a9a49a016e`**.

**Verdict: frontend checks executed; functional acceptance remains FAIL because P3-004 still blocks qualification. Unit tests, types, lint, production build and generated API-type consistency passed. Chromium completed with 3 passes and 1 failure. This cycle changes reports/log only, not product behavior or test expectations.**

## Scope and environment

Tested the frontend currently integrated on the QA branch. Separate unmerged frontend redesign branches were not imported or tested. Existing Next.js15/React19/TypeScript/Tailwind implementation and installed locked dependencies were reused on Windows with Node24.13.0/npm11.6.2, Chromium via Playwright and PostgreSQL16.15.

Browser QA used `scripts/run_browser_qa.py` and `playwright.qa.config.ts`: API on127.0.0.1:8001, frontend on127.0.0.1:3001, `.next-qa` output and the disposable `solarops_test` database. Production build ran after browser servers stopped, using the same isolated output directory sequentially. The original demo API/frontend were not reused for browser assertions.

## Fresh executed results

| Check | Result | Scope/evidence |
| --- | --- | --- |
| Vitest | **7 passed**, 2.75s | `access.test.ts`4 and `format.test.ts`3 |
| TypeScript | PASS | `npm run typecheck`, no errors |
| ESLint | PASS | No lint warnings/errors; existing next-lint deprecation notice remains |
| Next.js production build | PASS | 26 pages generated; also checked types/lint |
| Generated API types | PASS | Before/after SHA256 identical after `npm run generate:api` |
| Chromium | **3 passed, 1 failed**, 55.1s | Four existing browser scenarios executed, no skip |
| Development/test isolation | PASS | Before/after development fingerprint unchanged; test role denied development CONNECT |

The unit and browser runs total11 test cases, with10 passing and1 failing. Build/lint/type checks are additional gates, not extra test cases. This is not a numeric code-coverage claim.

## What the unit tests verify

- `apps/web/src/lib/access.test.ts`: role workspace destinations, customer rejection from staff paths, safe handling of requested post-login paths, and rejection of external/protocol-relative redirects.
- `apps/web/src/lib/format.test.ts`: whole rupees→integer paise, invalid/fractional/negative bill input handling, paise display and watts→kilowatts display.

These tests do not replace server-side authorization or prove all React components work. Actual cookie/CSRF/API behavior is exercised by the browser scenarios against PostgreSQL.

## Browser results

| Scenario | Result | Behavior actually reached |
| --- | --- | --- |
| Original signup/customer-to-sales journey, `e2e/enquiry.spec.ts` | PASS | Signup, captured development OTP verification, login, enquiry submission, reload persistence, employee sales login, under-review update and customer status view |
| Seeded customer/sales qualification, `e2e/seeded.spec.ts` | **FAIL** | Login/dashboard, creation201, persisted detail/reload and early authorization checks reached; sales qualifying PATCH returned422 instead of200 |
| Seeded admin employee login, `e2e/seeded.spec.ts` | PASS | Ordinary employee login and database-backed Employees screen |
| Login/portal smoke, `e2e/smoke.spec.ts` | PASS | Login rendering, customer/staff form switching, password input type, signup link and no page errors |

The failing scenario did not execute its later qualified-status assertion or customer logout/relogin/refresh checks. Their historical success is not presented as a current pass.

## P3-004: qualification UI/API mismatch (open, high)

**Reproduce:** run the isolated browser command below, sign in as the prepared customer and submit an enquiry, then sign in as sales, choose Qualified and save the status. The seeded Playwright scenario automates this.

Expected: the UI collects required roof/grid details and successfully qualifies the enquiry, allowing the customer to track it.

Actual: PATCH `/api/v1/enquiries/{id}/qualification` returns **422**. `apps/web/src/app/sales/enquiries/[id]/page.tsx:save` sends only `{status, note}`. `apps/api/app/services/enquiry_service.py:qualify_enquiry` correctly requires `shadow_free_area_sqm` and `grid_connection_suitable` for Qualified when no prior values exist. The form provides no inputs for those prerequisites.

This is a product integration defect, not a database-startup failure or an incorrect success assertion. Proposed frontend correction: collect and send the validated fields. Backend validation and the browser assertion were retained. No implementation fix was made during this test/report cycle.

## Data and artifact protection

All destructive setup/migrations/seeding for browser QA targeted only `solarops_test`, which reached `d5f1a2b3c4e5` with44 tables/104 indexes. `solarops_dev` remained at `68d7cd857e38` with13 tables/27 indexes. Its protected user/enquiry/history fingerprint stayed unchanged (16 users,8 enquiries,14 history rows). Generated credentials, mailbox files, traces, screenshots and browser results remain ignored and are not included in the report/commit.

Historical `test 1 report.txt` and `test 3 report.txt` were preserved. Generated `next-env.d.ts` path changes from the isolated build and content-identical schema regeneration are restored before commit; they are not product changes.

## Commands executed

From `apps/api`, sequentially with the existing ignored local credentials/config:

```powershell
uv run python scripts/check_local_db.py verify
uv run python scripts/run_browser_qa.py
uv run python scripts/check_local_db.py verify
```

From `apps/web`:

```powershell
$env:SOLAROPS_NEXT_DIST_DIR='.next-qa'
$env:NEXT_TELEMETRY_DISABLED='1'
npm test
npm run typecheck
npm run lint
npm run build
npm run generate:api
```

The API schema file hash was compared before/after generation and matched exactly. Unit/type/lint checks ran while browser QA finished; production build waited until the browser server stopped. Do not run the isolated browser bootstrap concurrently with pytest because both own `solarops_test`.

## Limitations and publication

No new backend full-suite run, browser/device matrix, accessibility audit, visual regression, load test or coverage percentage was performed in this frontend cycle. Phase3 warehouse/installation UI pages on this branch remain planned placeholders. The earlier API fixes and successful GitHub CI run are historical context, not a claim that this browser failure is resolved. Existing CI web checks do not run Playwright; green CI cannot override the failed scenario above.

User explicitly confirmed publication to `origin/test/qa-integration` after results/report completion. This report, root `frontend test report.txt` and the appended `QA_ACTION_LOG.txt` are the intended artifacts. Commit/push SHA and remote verification are reported in chat after publication.
