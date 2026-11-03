# Final Release Verdict

Lifecycle follow-up, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`; baseline handoff `2b892fe3ec450ca1121afaaabdb1941d3f8716b9`. Final source/build SHA and post-commit smoke are in the delivered `FINAL_EXECUTION_MANIFEST.json`. Previous test counts are historical, not substituted for this run.

**INCOMPLETE — external provider and automated acceptance gates remain blocked.**

The payment credential blocker is now correctly isolated: all five internal journeys have passed in the supported real browser with explicit test-only funding and real PostgreSQL persistence. Warehouse, customer acknowledgment, serial warranty activation, repair/resolution and customer confirmation are no longer blocked by Razorpay credentials. No live or invented cash/provider settlement was used.

| Acceptance area | Status | Scope / remaining work |
|---|---|---|
|Internal J1–J5 business lifecycle|PASS for observed campaign|Actual forms/API/database across repair builds, same linked records, labelled synthetic events|
|Fresh complete lifecycle replay on final commit|NOT TESTED manually / BLOCKED in automated runner|Final committed build readback is verified; it is not substituted for a fresh full replay|
|Persistence and critical role/replay controls|PASS|Browser refresh/relogin plus direct DB/proxy negatives|
|Backend and frontend regression / lint / types / build / contracts|PASS|605 backend, 88 frontend; exact source/build manifest|
|Critical axe/overflow and keyboard smoke|PASS for tested cases|42 route/viewports and explicit modal/error checks; not full assistive-technology certification|
|Standalone Playwright browser regression / exact new-calendar regression|BLOCKED|macOS Chromium bootstrap permission denied; run unchanged assertion-bearing tests in supported environment|
|Actual Razorpay test checkout/callback/webhook acceptance|BLOCKED|Private authorized test key/secret and webhook secret absent|
|All remaining saved-record variants / full screen-reader acceptance|NOT TESTED|Estimate/bill/replacement variants and hardware assistive technology are not certified|

No confirmed P0 or unresolved P1 blocking the executed primary internal path remains. That statement is limited to observed scope. The requested stronger “INTERNAL PRODUCT ACCEPTANCE PASSED — EXTERNAL PAYMENT PROVIDER ACCEPTANCE BLOCKED” label is not used because it would omit the separately blocked automated browser gate and unexecuted acceptance variants.

Next execution: use a supported Chromium/CI runner without disabling macOS controls; run the three added browser regressions and existing primary release suites on a fresh controlled fixture set. Configure only authorized Razorpay TEST credentials privately for separate provider acceptance. No push, merge, public deployment or live financial transaction is authorized or performed.

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
