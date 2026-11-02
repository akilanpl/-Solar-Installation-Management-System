# Test Execution Report

Lifecycle follow-up, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`; baseline handoff `2b892fe3ec450ca1121afaaabdb1941d3f8716b9`. Final source/build SHA and post-commit smoke are in the delivered `FINAL_EXECUTION_MANIFEST.json`. Previous test counts are historical, not substituted for this run.

| Exact command / layer | Current result |
|---|---|
|`pytest --junitxml=../../var/evidence/lifecycle-final-backend.xml` (private environment explicitly passed)|PASS: 605 tests, zero failures/errors/skips, 646.58 s; one Starlette TestClient deprecation warning|
|`pytest tests/test_sandbox_capability.py tests/test_quotation_integrity.py tests/test_razorpay_boundary.py`|PASS: 35 targeted tests|
|`pytest tests/test_complete_launcher.py`|PASS: 5 cases, including active-listener preservation and TIME_WAIT restart|
|`npm test`|PASS: 88 tests / 18 files|
|`npm run typecheck`|PASS|
|`npm run lint`|PASS, zero warnings|
|`npm run build`|PASS; final post-commit build identity in manifest|
|`ruff check app tests scripts`|PASS|
|`python scripts/export_openapi.py` / `npm run generate:api` with SHA-256 comparison before/after|PASS, generated artifacts exactly reproduce source|
|`npx playwright test --config playwright.complete.config.ts lifecycle-persistence.spec.ts --project chromium`|BLOCKED: runner reports 3 launch failures before browser interaction; not product assertion failures or passing tests|
|Supported in-app browser J1–J5|PASS across repair builds with persisted synthetic lifecycle and separate roles; final committed build readback PASS, fresh full replay NOT TESTED|
|Axe WCAG 2A/AA/2.1AA, critical route/viewports|PASS measured violations after repairs; manual-review items and limits in browser report|
|Keyboard modal and invalid-form checks|PASS recorded subset; not full screen-reader certification|
|Proxy/API replay and cross-customer campaign|PASS, unchanged payment/order counts|
|Direct PostgreSQL linked-state readback|PASS: completed job, seven warranties, zero residual stock and closed complaint|

The full suite includes selected duplicated release-campaign regressions and a five-minute 10-RPS HTTP campaign. Counts are test executions, not newly authored distinct business scenarios. The earlier 604-test full run passed before the final launcher case; 605 is the later final run. All run logs/XML are stored privately in var/evidence; sanitized final XML/JSON is included in the evidence deliverable. No prior-turn 601/85 result is used as current verification.
