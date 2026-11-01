# PR CI repair implementation checkpoint

## PR #3 — frontend integration

Source branch: `fix/actual-frontend-integration`; target:
`integration/final-release`. Starting SHA:
`7f7b3883c1bcbd4da21146c197cc4067ee2909bb`.

Original failed [pushgate run 41204295708](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41204295708),
job `gate` 124546132401, step 8 `.pushgate/run.sh --mode=ci`:
`INCOMPLETE: 55.4/100; see missing_evidence`, exit 1. Ordinary API/web CI
run 41204295723 passed. Saved artifact 13043887350 confirms the executed
stages passed; mandatory campaign entries were not run.

### Actual defects and corrections

- `.pushgate/run.py` previously discarded a failed command's exit status
  whenever any JUnit existed, and could reuse stale passing XML. It now
  clears prior evidence, records each process outcome, rejects empty or
  malformed JUnit, and requires measured coverage artifacts.
- The configured line/branch/diff limits were not executed. The runner now
  collects actual branch coverage and evaluates 80% line, 70% branch and
  90% changed-statement thresholds. Coverage and YAML tools are locked dev
  dependencies. The diff comparison uses the PR base SHA in CI, or the
  explicitly configured target ref on push. Thresholds remain unchanged.
- Added a second complete backend run in reverse collection order, in a
  fresh process and sequentially against the same disposable schema. This
  exposed two previously intermittent installation signature failures.
- `app/db/session.py:build_engine` issued `SET TIME ZONE 'UTC'` inside an
  implicit DBAPI transaction. Returning a read-only/failed request to the
  pool rolled that setting back to the cluster default, Asia/Calcutta on
  this host. A read-only reproduction returned UTC then Asia/Calcutta from
  the same pooled connection. The connection hook now sets the timezone
  in temporary DBAPI autocommit mode and restores the prior mode.
- `installation_service.work_summary` hashed the timestamp representation
  rather than a canonical instant. The same arrival produced three hashes
  under UTC, Asia/Kolkata and America/New_York. Arrival is now serialized
  in UTC. Completion still verifies the original acceptance HMAC and
  permits an older signed timezone representation only when its complete
  signed summary matches the current summary after timezone normalization.
  Original signed payloads/HMACs are never rewritten.
- Added pinned Gitleaks 8.30.1 installation with upstream archive SHA256
  verification and redacted full-HEAD-ancestry scanning. Missing scanner,
  missing/malformed output and any finding fail closed.
- Added an isolated browser runner with explicit local `solarops_test`
  acknowledgment, active-session/port checks, fresh servers on 8011/3011,
  private disposable credentials, isolated mailbox/evidence/build files,
  and unique result directories. Existing browser tests no longer load
  development account passwords. Fixed ambiguous password/logout locators
  and supplied real qualification prerequisites without weakening assertions.
- Added a private local Razorpay test-key setup/check utility. It performs
  only a read-only authentication check, refuses live keys, and does not
  enable checkout or claim provider settlement. Keys remain account-owned
  and are not configured in this repository. See LOCAL_RAZORPAY_SETUP.md.

### Observed validation before exact-commit run

- Backend baseline: 159 passed.
- Added access/configuration/pricing/read-scope tests passed; measured
  combined coverage rose from 61.739% to 70.761% branches, with unchanged
  source behavior. A subsequent fresh normal-order suite passed 283 tests.
- Reverse-order suite before timezone fix: 281 passed, 2 failed (customer
  signature 409). Two focused timezone regressions both failed before the
  fix, proving the root cause independently of test ordering.
- Related timezone/installation/warehouse run after the primary fix:
  44 passed. Expanded timezone/legacy-preservation suite: 9 passed.
- Gate self-tests: 18 passed, including malformed/stale evidence,
  configured thresholds, diff coverage and browser reset refusal guards.
- Existing Chromium acceptance: 4 passed against disposable PostgreSQL,
  with registration/mailbox verification, enquiry qualification,
  refresh/logout/relogin persistence and normal admin login.
- History scanner on starting HEAD: 22 commits scanned, no leaks found.
- Typecheck, lint and optimized build passed after installing the actual
  PR lockfile. The first reused dependency installation lacked lucide-react;
  one npm install hit ECONNRESET, and its cached retry succeeded.

### Committed backend verification and browser follow-up

Implementation commit `d02c485c5d71258184b6b679c1c3a00d4ed65773` passed
292 backend tests in each of normal and reverse order. Fresh measured
coverage: 90.060% line, 71.013% branch, 100% changed backend statements.
Gate self-tests, lint, frontend 27 tests, typecheck, lint, optimized build,
dependency audit and full-ancestry secret scan passed. The gate remained
INCOMPLETE; one browser case exposed another real stale-response race.

`apps/web/src/app/sales/enquiries/[id]/page.tsx:Review.load` allowed the
discarded Strict Mode effect's late GET response to reset a form after the
sales user selected Qualified and started entering verified roof/grid data.
The trace captured a filled roof area followed by a removed grid control.
The effect now cancels state/error updates from an obsolete invocation.
The seeded browser regression holds and releases actual persisted-record
GET responses, then asserts that status, roof area and grid choice survive.
All four browser cases passed after the fix; the final controlled-latency
case passed twice more (38.9 seconds). No assertions or time limits were
weakened. Frontend 27 tests and optimized 30-page build passed again.

The shell launcher now uses the project virtual environment, ensuring that
the runner can import its locked YAML dependency on GitHub-hosted machines.
Its Bash syntax check passed. API/client contract regeneration and final
remote checks follow publication; no PR is claimed green here.

### Remaining release blockers

The gate intentionally remains incomplete for the full customer-to-warranty
browser journey, load/resilience/accessibility campaign, complete mutation
evidence, main-baseline ratchet, and unfinished Phase 3 location allocation,
partial fulfilment, inspected returns, procurement, scheduling and serial
policy requirements. Four browser tests do not satisfy the complete journey.
Real provider evidence additionally requires locally entered account-owned
sandbox credentials and full checkout/webhook/reconciliation implementation.

No development migration/reset, live payment, PR merge/approval/close,
force-push or branch deletion was performed. Historical QA reports were
preserved. Publication is limited to normal pushes to the authorized source
branch after verification; current result remains STILL FAILING / BLOCKED
until remaining requirements have real evidence.

## Remaining PR inventory

| PR | Starting head | Failed run | Original result |
|---|---|---|---|
| #4 | adc216674a5cb0c3f1d82ff4b90450a99df7f47d | 41249300067 | INCOMPLETE 56.6/100 |
| #5 | 798c6b4793abea67cc359b82167678f324b677f7 | 41267132478 | INCOMPLETE 56.8/100 |
| #6 | 5b1149c8f9805d0ec0edfd36406b48d04d2dd017 | 41249306140 | INCOMPLETE 56.6/100 |
| #7 | 292b53d9f431568e950c0ed807c0795155625645 | 41249309029 | INCOMPLETE 56.6/100; merge conflicts |

Each branch must be checked for compatibility before reusing a correction.
