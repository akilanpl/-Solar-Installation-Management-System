# Phase 3 final verification report

Branch: `feature/phase3-warehouse-installation`.
Worktree: `/Users/akilan/Downloads/SOLOPS-phase3`.
Acceptance: a working and verified Phase 1–3 backend. No frontend and
no QA-owned changes were made. Phase 4 was not started.

## Environment proof (executed commands)

1. `pwd -P` returns `/Users/akilan/Downloads/SOLOPS-phase3`.
2. `git branch --show-current` returns
   `feature/phase3-warehouse-installation`.
3. The worktree is writable (created and removed a probe file).
4. PostgreSQL 15 (Homebrew, port 5432) accepts connections; both
   `solarops` and `solarops_test` answer. Note: the default shell
   sandbox blocks TCP to 127.0.0.1, so every database-backed command
   in this session ran with escalated sandbox permission. That is a
   sandbox property, not a repository or database problem.
5. `uv sync --frozen` completes with `UV_CACHE_DIR=/tmp/uv-cache-phase3`
   (the home-directory cache is blocked in this environment). The
   isolated `solarops_test` database exists and the test guard refuses
   any other database name.
6. The pre-existing Phase 1–2 suite passed before any Phase 3 edit:
   46 passed, `ruff check` clean.

## What was built

- Warehouse inventory: stock operations (`draft`/`ready`/`done`/
  `cancelled`), ledger-only on-hand, reservations, serial scans,
  replenishment request/decision.
- Picking (delivery creation with availability check), delivery
  state machine, installation scheduling slots, technician job
  execution (arrival, customer OTP, evidence, signature, completion),
  and warranty activation/void.
- Integration: order confirmation auto-creates reservations; delivery
  confirmation consumes them and activates the warranty.
- Contract updates: `contracts/generated/openapi.json` regenerated
  from the app; `docs/api/API_CONTRACTS.md` lists the new routes as
  implemented.

## Test evidence (PostgreSQL-backed, all observed this session)

- Full suite: **58 passed** (`apps/api`, `uv run pytest`).
  Phase 1–2 files: 46 passed, unchanged. New
  `tests/test_phase3_warehouse_installation.py`: **12 passed**.
- `ruff check app tests scripts`: clean.
- Alembic `upgrade head` applies `d5f1a2b3c4e5` on the development
  database; the test session migrates from an empty schema each run.
- Coverage by layer: unit (ledger math, transitions), integration
  (order to completed installation end to end), concurrency (two
  racing validations, one winner), security (customer 403s,
  staff-decision 403, foreign-job 404s), cross-phase (enquiry through
  survey, quotation, cash payment, order, reservation, receipt,
  delivery, warranty, scheduling, job).
- OpenAPI export reproduces the committed contract file content
  (exported from the running app in this session).

## Defects found and fixed

1. Deliveries skipped the stock availability check: a delivery could
   be prepared for an order with no stock on hand. Fixed in
   `_check_pick_availability` (`fulfillment_service.py`); new test
   `test_picking_without_stock_fails` proves the 409.
2. Reservations were created but never consumed: `consume_reservations`
   was dead code. Delivery confirmation now consumes them in the same
   transaction as the warranty activation; the warranty test asserts
   the `consumed` state.
3. Dead `issue_job_otp` helper duplicated OTP issuance. Removed; OTP
   issuance lives only in `installation_service.create_job`.

Each fix was followed by a full green rerun (58 passed).

## Unverified risks and handoff

- Browser and frontend checks were not run: the web app is teammate
  2's scope and QA is teammate 3's.
- The development database `solarops` was migrated but never reset or
  deleted, per instructions. `solarops_test` is rebuilt by the test
  session.
- Recommended next steps for the other teammates: teammate 2 builds
  the warehouse, delivery, scheduling, job, and warranty screens
  against the implemented contract table; teammate 3 runs the
  independent QA pass and the Playwright enquiry flow.
- All work is uncommitted in the working tree (local commits were
  permitted but not required). Files changed or added are listed by
  `git status`: 3 modified source/contract files plus the migration,
  2 routers, 2 services, 1 model, 1 schema, 1 test file, and 4 docs.
  Nothing was pushed, no PR opened, no branch merged.
