# Phase 4A test report

Executed on this branch. Counts below are observed results, not projections.

## Backend — 179 passed, 0 failed

`cd apps/api && uv run pytest` against a disposable `solarops_test` database
(migrated from empty by Alembic, including `f4a7b2c1d093`):

- Baseline carried forward: 147 passed (Phases 1–3, migration-consistency,
  security hardening).
- New `tests/test_phase4a_support.py`: 32 passed, covering customer creation
  with an installed serial, other-customer order rejection (404), reserved
  serial rejection (`serial_not_installed`), unknown serial (404), idempotent
  replay and key conflict, missing key (400), site ownership and cross-site
  rejection, triage classification, early close/ready rejection, customer
  close forbidden (403), owner-first assignment then repair-job creation
  (regression for the assigned-to-assigned bug E2E found), job replay and
  second-open-job rejection, the 5-open-job cap, inactive/non-technician
  assignees (404), bad support owner (404), technician isolation (own ticket
  detail, own list; stranger 404; sales 403/404), submit gates
  (`arrival_required`, `diagnostics_required`), post-submit update rejection,
  impossible work times (422), unknown part (404), attachment type/size
  validation, job-linked upload with mismatch cleanup (404, no orphan row),
  attachment listing, support download, missing download (404),
  cross-customer download (404), the full Leela accept-and-close flow with
  fresh-login persistence and the ten-event history, support
  self-confirmation (403), cross-customer confirmation (404), replay
  (`duplicate_confirmation`), dispute reopening with close blocked, stale
  version after a new resolution (`stale_summary`), closed-ticket reopening,
  failed-confirmation rollback (no acknowledgment row, status unchanged),
  two-thread concurrent confirmation (exactly one winner, one acknowledgment
  row), customer and support cancellation with the open job cancelled,
  late-cancel and premature-reopen rejection, note recording with
  closed-ticket rejection, request-info round trip back to `triaged` with
  pre-triage and wrong-state rejection, escalation with priority change or
  kept priority and pre-triage rejection, repair-job ticket filter, and the
  support staff directory (technician/support/admin allowed, customer 403,
  bad role 422).
- `tests/test_phase3_migrations.py` updated for the new head: migrated schema
  matches SQLAlchemy metadata exactly, and the downgrade/upgrade round trip
  preserves a Phase 1 record with all five Phase 4A tables, foreign keys, and
  constraints present.
- `ruff check app tests scripts`: clean.

## Frontend — 10 passed, typecheck/lint/build clean

`cd apps/web`: `npm test` 3 files / 10 tests passed (7 carried, 3 new for the
ticket status labels and idempotency-key alphabet). `tsc --noEmit`, `next
lint`, and `next build` (28/28 pages) all pass with the new customer
complaint, support inbox/ticket, and technician repair routes.

## Browser E2E — 1 passed; pre-existing specs unaffected

`cd apps/web && npx playwright test tickets` (Chromium, real PostgreSQL
`solarops_dev` reset + migrated + seeded before the run): **1 passed**.
The spec drives the acceptance scenario through the real UI: customer signup
with mailbox verification, the full order-to-installed pipeline via API,
complaint raised with the installed serial, support triage, owner assignment,
repair-job creation, technician arrival/diagnostics/work/submit, resolution
ready, customer review and accept, support close, reload persistence, and a
final API listing asserting `closed`.

`npx playwright test smoke enquiry`: **2 passed**. `seeded.spec.ts` was not
run: it requires `var/demo-credentials.json`, which does not exist in this
environment (pre-existing condition, same as baseline).

## Repo quality campaign for the docs SHA

`.pushgate/run.sh` with a disposable database: all 10 executed stages pass
(199 passing entries: lint, backend, frontend, typecheck, build,
dependency audit with zero high/critical). Line coverage 89.8% (threshold 80,
pass). Branch coverage 65.5% (threshold 70, fail) — pre-existing: the base
code without Phase 4A measures 61.7%, while the new Phase 4A files measure
83.7% branch coverage and lift the average. Aggregate
56.6/100 INCOMPLETE, blocked only by the hardcoded mandatory-campaign entries
(browser journey beyond this mission's spec, load, mutation, secret scan,
CI), exactly as at baseline (55.4). The pre-push hook therefore still refuses
the push by design; see the handoff.

## Bugs the gates caught

1. Repair-job creation failed when a support owner was assigned first
   (`assigned` → `assigned`). Fixed in `ticket_service.create_repair_job`
   (records history when already assigned) with a regression test.
2. Support detail crashed after job creation: the UI stored a
   `RepairJobResponse` in ticket state. Job creation now has its own handler.
3. Three React form handlers called `.reset()` on a nullified synthetic event
   after `await`. All capture the element first.

## Not verified

Load, mutation, coverage-percentage, and production-hosting evidence were not
run. No warranty billing (Phase 4B by design). One E2E run covers the happy
path plus API-level negatives; browser negatives beyond the suite were not run.
