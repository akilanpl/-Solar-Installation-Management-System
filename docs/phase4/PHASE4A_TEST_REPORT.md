# Phase 4A test report

Executed on this branch. Counts below are observed results, not projections.

## Backend — 166 passed, 0 failed

`cd apps/api && uv run pytest` against a disposable `solarops_test` database
(migrated from empty by Alembic, including `f4a7b2c1d093`):

- Baseline carried forward: 147 passed (Phases 1–3, migration-consistency,
  security hardening).
- New `tests/test_phase4a_support.py`: 19 passed, covering customer creation
  with an installed serial, other-customer order rejection (404), reserved
  serial rejection (`serial_not_installed`), unknown serial (404), idempotent
  replay and key conflict, triage classification, early close/ready rejection,
  customer close forbidden (403), owner-first assignment then repair-job
  creation (regression for the assigned-to-assigned bug E2E found),
  technician isolation (other technician sees nothing, 404), exact-slot clash
  (`technician_unavailable`), submit gates (`arrival_required`,
  `diagnostics_required`), impossible work times (422), unknown part (404),
  attachment type/size validation and authorized download with cross-customer
  404, the full Leela accept-and-close flow with fresh-login persistence and
  the ten-event history, support self-confirmation (403), replay
  (`duplicate_confirmation`), dispute reopening with close blocked, stale
  version after a new resolution (`stale_summary`), closed-ticket reopening,
  failed-confirmation rollback (no acknowledgment row, status unchanged),
  two-thread concurrent confirmation (exactly one winner, one acknowledgment
  row), cancellation before work, request-info round trip back to `triaged`,
  escalation with priority change, and the support staff directory with a
  customer 403.
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
