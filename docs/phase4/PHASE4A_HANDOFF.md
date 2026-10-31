# Phase 4A handoff — reviewable checkpoint

## What was built

A complete, persistent, secure customer complaint-to-confirmed-resolution
workflow on the integrated Phase 1–3 base (`ebf107b`), per
`docs/release/PHASE4_ENGINEERING_GATE.md` § Support tickets and
Customer-confirmed resolution. No Phase 4B–4E work was started.

- Backend: `apps/api/app/models/support.py`, `schemas/support.py`,
  `services/ticket_service.py`, `api/v1/tickets.py` (28 endpoints), migration
  `f4a7b2c1d093_phase4a_support_tickets.py` (new head).
- Frontend: customer Complaints + Complaint Detail, support Inbox + Ticket
  Detail, technician Repairs + Repair Detail (`apps/web/src/components/tickets.tsx`,
  7 routes), existing visual language and components reused.
- Contracts: `contracts/generated/openapi.json` + `apps/web/src/generated/schema.ts`
  regenerated from the app, never hand-edited. `docs/api/API_CONTRACTS.md`
  implemented/planned tables updated.
- Tests: `apps/api/tests/test_phase4a_support.py` (19), `apps/web/src/lib/tickets.test.ts`
  (3), `apps/web/e2e/tickets.spec.ts` (browser acceptance).
- Docs: this folder (`PHASE4A_ARCHITECTURE.md`, `PHASE4A_API_CONTRACTS.md`,
  `PHASE4A_TEST_REPORT.md`, `PHASE4A_HANDOFF.md`).

## Verification (all observed)

- Backend: **166 passed**, ruff clean. Fresh-login persistence, replay/stale/
  duplicate rejection, concurrency single-winner, and rollback proven.
- Frontend: **10 passed**, typecheck/lint/build clean (28/28 pages).
- Browser: Leela acceptance **passed** in Chromium against real PostgreSQL;
  smoke + enquiry specs still pass (2 passed).
- Migration `f4a7b2c1d093` applied from empty (test bootstrap), by round-trip
  downgrade/upgrade, and on a fresh `solarops_dev` (reset + seed).
- Acceptance scenario proven transition by transition; the closed ticket
  persists across logout/login and reload.

## Commits (branch `feature/phase4a-support`, no force-push, `main` untouched)

- `0044d8a` Phase 4A backend (models, migration, service, API, 19 tests, contracts)
- `7ee8f77` Phase 4A frontend (workspaces, regenerated types)
- `ff5ef45` Acceptance spec and contract docs
- `2f2802a` E2E-driven fixes with regression test

PR: opened after final docs commit (URL below).

## Remaining limitations (explicit)

1. Warranty billing, coverage decisions, and charges are Phase 4B: parts are
   recorded as catalogue codes + quantities only; no stock moves, no prices.
   Stated in code comments, UI copy, and the API contract doc.
2. Technician eligibility is active-role + open-job cap (5) + exact-slot clash.
   Skills, working hours, leave, travel, and overrides do not exist (the
   integration release lists them as missing); nothing is invented to cover it.
3. No notification provider exists, so none is sent or claimed.
4. `seeded.spec.ts` not run (missing `var/demo-credentials.json`, pre-existing).
5. No load/mutation/coverage-percent/production-hosting evidence.

## Readiness verdict

**READY FOR REVIEW as a Phase 4A checkpoint — VERIFIED** for complaint intake,
triage, assignment, technician repair recording, versioned customer-confirmed
resolution, closure/reopening, attachments, history, and persistence. **NOT
READY** for warranty billing or any Phase 4B–4E scope. Do not merge to `main`
without review.
