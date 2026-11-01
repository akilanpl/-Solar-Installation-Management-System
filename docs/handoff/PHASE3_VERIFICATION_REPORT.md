# Phase 3 final acceptance audit report

Branch: `feature/phase3-warehouse-installation`.
Acceptance: a working and verified Phase 1–3 backend. No frontend and
no QA-owned changes were made. Phase 4 was not started.

Status words: VERIFIED (proven by an executed check this session),
PARTIAL (works, with a named coverage or capability gap), BLOCKED
(could not be checked, with the reason), NOT IMPLEMENTED (explicitly
out of scope).

## Environment proof

1. VERIFIED — `pwd -P` returns
   `/Users/akilan/Downloads/SOLOPS-phase3`.
2. VERIFIED — `git branch --show-current` returns
   `feature/phase3-warehouse-installation`.
3. VERIFIED — the worktree is writable (probe file created and
   removed; this session also wrote, migrated, and committed here).
4. VERIFIED — PostgreSQL 15 on port 5432 answers for `solarops` and
   `solarops_test`. Note: the default shell sandbox blocks TCP to
   127.0.0.1, so every database-backed command ran with escalated
   sandbox permission. Sandbox property, not a repository problem.
5. VERIFIED — `uv sync --frozen` completes with
   `UV_CACHE_DIR=/tmp/uv-cache-phase3`; the test guard refuses any
   database except `solarops_test`.
6. VERIFIED — the 46 pre-existing Phase 1–2 tests passed before any
   Phase 3 edit and still pass now.

## Business-journey coverage (all VERIFIED, PostgreSQL-backed)

| Journey step | Result | Proof |
| --- | --- | --- |
| Enquiry to confirmed order (Phase 1–2 intact) | VERIFIED | 46 unchanged tests pass |
| Order auto-creates material reservations | VERIFIED | `test_confirmed_order_creates_reservations` |
| Receipt/transfer/adjustment ledger math | VERIFIED | receipt, failed-ledger, location tests |
| Two orders competing for one stock lot | VERIFIED | `test_competing_orders_cannot_pick_the_same_stock`: second gets 409, no rows, loser stays reserved |
| Failed pick creates nothing | VERIFIED | delivery/ledger counts unchanged in void test |
| Failed validation leaves ledger unchanged | VERIFIED | `test_failed_transfer_and_delivery_leave_ledger_unchanged` |
| Concurrent same-operation validation, one winner | VERIFIED | `test_concurrent_validation_has_a_single_winner` |
| Concurrent cross-operation picks serialize | VERIFIED | `test_concurrent_picks_serialize_on_component_locks` |
| Duplicate delivery confirmation rejected | VERIFIED | `test_duplicate_delivery_confirmation_fails` |
| Delivery cancel restocks MAIN | VERIFIED | `test_delivery_cancel_restocks_main` |
| Location consistency (SITE needs transfer) | VERIFIED | `test_site_stock_must_transfer_to_main_before_pick` |
| Serial scan uniqueness | VERIFIED | `test_serial_scan_is_unique_and_rejects_done_operations` |
| Serial assign, mismatch, install on confirm | VERIFIED | `test_serial_assign_install_and_mismatch` |
| Unauthorized technician blocked (404) | VERIFIED | `test_foreign_technician_cannot_touch_assigned_job` |
| Expired and reused OTP rejected | VERIFIED | `test_expired_and_reused_customer_otp_fail` |
| Completion gates (OTP, evidence, signature) | VERIFIED | `test_job_completion_requires_otp_evidence_and_signature` |
| Customer cannot touch warehouse | VERIFIED | security test, 403/404 asserts |
| Warranty created at confirm, void guarded | VERIFIED | confirm, void, duplicate-void asserts |
| Full order-to-completed-installation journey | VERIFIED | `test_cross_phase_order_to_completed_installation` |
| Migration from empty + downgrade round-trip | VERIFIED | `solarops_fresh` disposable check (see below) |

## Migration check on a disposable database (VERIFIED)

`solarops_fresh` was created (superuser `akilan` via the `/tmp`
socket; the `solarops` role lacks `CREATEDB`), `alembic upgrade head`
applied all four revisions from empty, `downgrade -1` plus
`upgrade head` round-tripped, seeds held 7 roles, 12 packages and
2 locations (`MAIN`, `SITE`), and the database was dropped
afterwards. Development data was never touched: `solarops` still
holds its 7 users, `solarops_test` is rebuilt by the test session.

## Defects found and fixed this audit

1. VERIFIED fixed — deliveries never deducted ledger stock, so two
   orders could pick the same goods. Creation now checks MAIN
   on-hand under a component lock and deducts it atomically.
2. VERIFIED fixed — concurrent validations across operations did not
   serialize. `lock_components` now locks catalogue rows in sorted
   order in both `validate_operation` and the pick path.
3. VERIFIED fixed — serials could never attach to an order
   (`order_id` stayed null). New `POST /serials/{id}/assign` plus
   auto-install at delivery confirmation close the loop.
4. VERIFIED fixed — job reads returned 403 for a foreign technician
   while writes returned 404, leaking job existence. Reads now
   return 404, matching the write path.

## PARTIAL (works, named gap)

- `threshold_suggestion` has no dedicated test; ledger math around
  it is covered indirectly.
- Delivery list filters: the owner-customer path is asserted; staff
  list paths are exercised but not asserted per role.
- Same-key idempotent replay is asserted for operations; the
  delivery replay path returns the original but has no dedicated
  replay test.
- Picks deduct from MAIN only. Multi-location allocation is a
  documented rule, not a silent behavior.

## NOT IMPLEMENTED (explicit Phase 4 candidates)

Replenishment auto-receiving, skill-based recommendations,
dispatcher overrides, customer self-scheduling, partial deliveries
and returns, serial-level picking (serials attach to orders, not
delivery lines), historical as-of-date stock queries, no-SMS OTP
channel beyond the one-time `customer_code`.

## BLOCKED

None for the backend scope. Browser and end-to-end UI checks belong
to teammate 2 (frontend) and teammate 3 (independent QA) and were
not attempted here.

## Final gates (this session, observed)

- `uv run ruff check app tests scripts`: clean.
- `uv run pytest`: 67 passed (46 Phase 1–2 + 21 Phase 3).
- `scripts/export_openapi.py` reproduces the committed contract.
- Working tree committed locally; nothing pushed, no PR, no merge.

## Readiness verdict

Backend VERIFIED for the acceptance scope, with the PARTIAL items
above as the honest residue. The remaining work is teammate 2's
screens against the implemented contract table and teammate 3's
independent QA pass — not backend rework.
