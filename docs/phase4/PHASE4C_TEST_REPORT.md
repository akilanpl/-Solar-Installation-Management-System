# Phase 4C local verification report

Verdict: **verified local development checkpoint; production release gate FAIL**.
The local functional checks pass. The unchanged repository-wide branch coverage
gate remains below 70%; live-provider and release evidence is absent.

## Provenance and environment

- Preserved Phase 4B base: `26a5f129e1eeea5ad772ab4e1b8c5f8f6d43bc3d`.
- Tested runtime source: `9d49099e0b607772f59005c06f52025375ff9081`.
- Implementation/harness head: `597eda213d79edc0cc76c3268188e7c07c69f680`.
  Its API/UI runtime bytes are identical to the tested runtime source; subsequent
  changes are verification documentation and evidence. The final branch SHA is
  sealed in the worktree's `var/phase4c/FINAL_CHECKPOINT.json` after the last commit.
- Branch/worktree: `feature/phase4c-finance-admin`, `~/Downloads/SOLOPS-phase4c`.
- Python 3.12.13; PostgreSQL 15.19 Homebrew; Node 25.9.0; npm 11.12.1;
  Next.js 15.5.28. Locked dependencies were used without lockfile changes.
- Backend tests: only `solarops_release_test_20261113`, localhost port 5432.
- Browser: only `solarops_4c_preview`, production Next.js port 3143, API 8143.
- Browser engine/version was not independently identified for Codex IAB. No
  Firefox, Safari, mobile-device or other-browser pass is claimed.

## Executed checks

| Check | Observed outcome |
| --- | --- |
| Inherited exact-base backend baseline | PASS: 203 tests, 196.94 seconds |
| Inherited frontend baseline | PASS: 12 tests; lint and typecheck pass |
| Final backend `coverage run --branch --source=app -m pytest` | PASS: 244 tests, 265.82 seconds; 203 inherited + 41 finance cases |
| SQLAlchemy/Alembic metadata and downgrade/upgrade | PASS in inherited full suite; original enquiry preserved, finance tables included |
| Ruff `check app tests scripts` | PASS; no threshold or test changes to conceal failures |
| `npm test` | PASS: 12 existing frontend unit tests |
| `npm run typecheck` | PASS |
| `npm run lint` | PASS; inherited Next lint deprecation notice remains |
| `npm run build` | PASS; production pages include all four finance workspaces |
| OpenAPI export + `npm run generate:api` + Git diff | PASS; regenerated files are identical to committed contracts |
| Five requested real-browser scenarios | PASS through Codex managed browser, real API and PostgreSQL |
| Playwright CLI launch | BLOCKED: four Chromium launch failures before app interaction; no CLI application PASS claimed |
| Read-only independent source/ledger/export reconciliation | PASS; raw ledger balances, dashboard margins, settlement count and downloaded CSV bytes agree |
| Provider / government integration | NOT RUN: none is connected; no real transaction/submission attempted |
| Full performance/resilience/accessibility/mobile campaign | NOT RUN; outside this bounded local verification |

The backend emits one inherited Starlette/httpx deprecation warning. npm install
reported 16 moderate dependency advisories on the inherited locked tree; no
unrelated dependency upgrades were attempted. This is not a dependency security
certification. Unit test counts are not presented as browser or provider evidence.

## Coverage and unchanged gates

| Scope | Statement/line coverage | Branch coverage |
| --- | ---: | ---: |
| Exact-base inherited source | 89.027% | 63.738% |
| Final whole backend | 89.643% (6604/7367) | 65.839% (1114/1692) |
| New finance files only | 93.878% (874/931) | 77.519% (200/258) |
| Changed executable backend lines | 93.891% (876/933) | Not asserted as a separate diff-branch metric |

Configured thresholds remain line 80%, branch 70%, diff line 90%. Whole-backend
line and measured diff-line checks pass. **Whole-backend branch coverage fails**;
the configured evaluator exits 1. The pre-existing branch shortfall is separate
from finance's 77.519% branch coverage. No tests were removed, skipped, weakened,
or replaced with mocks to improve coverage. Uncovered finance branches remain
visible in the detailed local JSON and coverage summary.

Baseline reporting was performed against an immutable `git archive` source
snapshot. Coverage arcs from the actual pre-change run were remapped to those
original files. Reporting the baseline against newly added finance files would
incorrectly include those unexecuted files in the baseline denominator. No new
finance file had executed baseline arcs.

## Exact browser results and persistence

The browser used the visible sign-in forms, role-specific workspace navigation,
finance command forms, actual file chooser/upload, source-record drill-downs and
CSV download. The database and app were not replaced with mock responses.

| Scenario | Final observable result |
| --- | --- |
| Profitable installation and accepted repair | `ORD-2026-000001`: recognized ₹80,520, actual material ₹9, approved labour ₹60, profit ₹80,451; reconciliation Complete |
| Loss-making installation | `ORD-2026-000002`: recognized ₹80,400, actual material ₹7,58,976, profit −₹6,78,576; reconciliation Complete |
| Technician payable | ₹60 approved, visible `₹60.00 unsettled`, zero settlement records; approval caused no cash movement |
| Customer subsidy workflow | Consent recorded; missing checklist initially electricity bill + identity, then None after uploads; sales reviewed; no government submission/approval/disbursement |
| Approved Phase 4B bill | `INV-2026-000001` imported as 12000 net + 2160 original tax = 14160 paise; immutable accepted-estimate snapshot retained |
| Original cash reconciliation | Two actual synthetic manually verified source receipts imported once: cash ₹1,89,744; remaining service receivable ₹141.60; advances zero |

The first installation was deliberately observed as incomplete after new repair
source activity, then reconciled through explicit Phase 4B material consumption,
actual valuation, recognition and a renewed completeness attestation. The final
service restart and browser reload retained both complete profit rows, the
reviewed subsidy count, unpaid liability and no browser console errors.

The final browser-downloaded CSV is committed as
`evidence/PHASE4C_BROWSER_EXPORTED_PROFIT.csv`. SHA-256:
`4fced25a618650d34792fd579f9e288a91ebf3c2f5428150399ac90badd68d0b`.
A separate read-only database/service verification reproduced the exact bytes.
Screenshots of the customer checklist, unpaid technician view and final dashboard
were captured/displayed in chat; no screenshot file is falsely claimed in Git.
The browser's default-download CSV was moved into the task-owned evidence folder;
no acceptance-export file remains outside the worktree.

All figures and documents in these scenarios are clearly synthetic fixtures.
Tiny material valuations and the negative case are test inputs, not claimed real
business results or approved operational cost policies.

## Scoped defect log and change explanation

| ID | Finding | Result/evidence |
| --- | --- | --- |
| C4C-01 | Stock movements lack actual acquisition valuation; quote prices would fabricate profit | Actual-cost evidence required; missing valuations block completeness; profit tests and browser source movement reconciliation |
| C4C-02 | Existing installation completion helper can omit delivery | Acceptance fixtures execute real receipt/delivery; missing stock remains incomplete, shared installation code untouched |
| C4C-03 | Equivalent timezone offsets change inherited work-summary hashes | Preview DB default set to UTC; shared code not changed; integration owner should fix canonical timestamp hashing separately |
| C4C-04 | New repair bills/consumption, cash receipts or later finance changes could leave an old reconciliation marked complete | Source/attestation checks added; browser observed incomplete → Complete after actual reconciliation |
| C4C-05 | Retrying an adjustment key against a different payable/order could return an unrelated record | Source-bound retry checks; real second-order and second-payable regression paths |
| C4C-06 | Transaction-start timestamps can misorder serialized domain events | Event time stamped after finance lock; two-session chronological regression |
| C4C-07 | Approval could be misread as a bank transfer | Separate immutable settlement events and live outstanding balance; browser shows approved liability with zero settlements |

The accounting flow is source → immutable approved domain record → balanced
journal → report. Source snapshots explain the money; journal lines explain the
balances; reversal/adjustment events explain corrections. No dashboard cache or
hardcoded metric supplies financial truth.

## Release checklist and environment unblock plan

- [x] Assigned worktree, exact preserved base and ancestry verified.
- [x] Task-owned disposable databases and unique ports used.
- [x] Additive migration and inherited schema round-trip checks pass.
- [x] Finance authorization, immutability, idempotency, strict money, rounding,
  reversal, concurrency, rollback and insufficient-data cases executed.
- [x] Five actual browser scenarios and persisted source reconciliation executed.
- [x] Ruff, backend/frontend tests, typecheck, lint, contracts and production build.
- [x] Local commits retained; hooks unchanged; no push/merge/deploy.
- [ ] Whole-repository branch coverage 70% gate: FAIL, inherited owner/integration
  must add meaningful missing branch coverage; do not lower the threshold.
- [ ] CLI browser rerun: developer/integration owner must run the supplied config
  outside the restrictive macOS sandbox after stopping only this task's preview.
- [ ] Accountant/business approval for real recognition, GST, provision, labour,
  correction, evidence and settlement policies.
- [ ] Provider credentials/signatures, real settlement/refund reconciliation,
  government release evidence, operational backup/retention/security/release QA.

The independently exercised local flows do not constitute a production release
certification or a second-person code/security audit. No production-ready claim
is made. Detailed local command logs and coverage artifacts remain gitignored
under `var/phase4c/evidence`; compact observed evidence is committed alongside
this report. Rerun commands and the safe environment setup are in the local
runbook. Further work is limited to integration/release blockers, not another
SolarOps phase.
