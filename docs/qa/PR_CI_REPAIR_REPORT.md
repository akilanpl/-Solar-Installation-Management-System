# SolarOps PR CI repair checkpoint

## PR #4 — Phase 4A support

Source `feature/phase4a-support`, target `integration/final-release`.
Starting source SHA `adc216674a5cb0c3f1d82ff4b90450a99df7f47d`.
Original failed [run 41249300067](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41249300067),
job `gate` 124679255142, step 8 `.pushgate/run.sh --mode=ci`.

SHA256-verified artifact 13060985455 showed branch coverage 727/1110,
65.495%, below the configured 70%; line coverage passed. No other executed
stage failed. The report additionally recorded unexecuted mandatory release
campaigns and returned INCOMPLETE 56.6/100.

### Corrections and why they work

- Added actual negative service/ownership/input/pricing regression cases.
  These exercise role denial before I/O, owner/stranger read boundaries,
  missing-record rollback, malformed identity fields and paise rounding.
  They add assertions rather than lower coverage limits or delete tests.
- Before selectively reusing the PR #3 correction, compared baseline
  database, installation, quotation, stock, payment, survey, order and
  fulfilment services: their original implementations were byte-identical.
  Fixed the connection UTC setting being undone by transaction rollback
  and canonicalized work-summary instants. Nine timezone/legacy-acceptance
  regressions verify old signed payloads and HMACs remain unchanged.
- Upgraded the existing gate to preserve failed process status even with
  partial JUnit, clear stale evidence, reject malformed/missing test XML,
  measure configured line/branch/diff coverage, execute a second backend
  order, scan actual commit history, and run browser acceptance safely.
  The launcher uses the locked project interpreter. No required check,
  threshold, mandatory placeholder or business invariant was disabled.
- This branch's qualification form omitted the backend's verified roof and
  grid fields (historical P3-004). Added the existing generated contract
  fields and obsolete-effect cancellation so a late initial GET cannot
  overwrite edits. The real-response latency regression verifies retained
  status, roof area and grid selection, followed by saved persistence.
- Browser acceptance now seeds private disposable accounts and starts fresh
  API/UI servers on 8011/3011. Both seeded and support-ticket tests use those
  credentials instead of reading development passwords. The older signup
  label includes help text, so its input-name selector is required rather
  than the newer UI's exact label. Tests wait for a successful authenticated
  session response and retain all assertions and original time limits.

### Validation

Disposable `solarops_test` only; expected Alembic head `f4a7b2c1d093`.
Fresh branch migrations, ORM parity, preservation/round-trip tests and the
full API suite passed. No development schema was reset, migrated or seeded.

| Check | Observed result |
|---|---|
| Frozen Python and npm installations | Pass |
| Full backend, normal order | 312 passed, 213.41 seconds |
| Full backend, reverse order | 312 passed, 196.30 seconds |
| Line coverage | 4106/4511 = 91.022%, threshold 80% |
| Branch coverage | 818/1118 = 73.166%, threshold 70% |
| Changed backend statements | 719/746 = 96.381%, threshold 90% |
| Frontend unit tests | 10 passed |
| Typecheck / lint / optimized build | Pass after replacing prior branch's generated Next routes |
| Existing Chromium cases | 5 passed, including customer-confirmed support repair |
| Gate self-tests | 18 passed |
| Commit history scan | 26 commits; no findings |
| OpenAPI/client regeneration | No contract changes |

The initial local gate recorded stale generated route errors from the reused
PR #3 build and incompatible older-label browser selectors. A current-branch
build and targeted typecheck passed; all five browser cases passed after
the selector/session-wait corrections. Earlier failing artifacts were retained.
No application fix was invented for the stale build cache.

Status: **FIXED LOCALLY** for the implemented failures. Commit/push and new
remote outcomes are recorded in the canonical workspace repair report after
publication. The release remains BLOCKED by unimplemented mandatory campaign
and product evidence; ordinary suite passes do not claim a complete release.

## PR #3 — published evidence

Normal pushes published d02c485, 2278ef4 and ancestry reconciliation
0e3c81a125e33068271184c7357f34869034751a to its existing source branch.
Ordinary CI succeeded on the latest source for push and PR events. Both
final gate runs 41274408064/41274405032 returned INCOMPLETE 67.9/100;
verified artifact 13071390478 shows every implemented stage passed. Merge
conflicts with the coverage-only target commit were resolved, with no
runtime change, and GitHub mergeability is true. No PR/main merge occurred.

## PRs #5–#7 and remaining requirements

Original verified branch coverage was 63.209%, 65.839% and 65.412% respectively.
All also lack the full release campaigns. Phase 4B now includes merged
Phase 4E source at 798c6b4; finance/intelligence siblings require explicit
migration and dependency reconciliation rather than blind patch copying.

Remaining mandatory evidence includes the full customer-to-warranty browser
campaign, load/resilience/accessibility, complete mutation coverage,
main-baseline ratchet, and unfinished Phase 3 allocation/partial delivery/
returns/procurement/scheduling/serial-policy requirements. Read-only local
Razorpay setup is prepared, but account-owned test keys and full provider
checkout/webhook/reconciliation evidence remain unavailable. No live payment
was performed. No threshold reduction, force push, branch deletion, PR
approval/closure or main merge was performed.
