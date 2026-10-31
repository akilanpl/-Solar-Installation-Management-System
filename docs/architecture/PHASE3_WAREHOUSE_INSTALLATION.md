# Phase 3 backend handbook: warehouse, delivery, installation, warranty

Phase 3 continues the Phase 2 confirmed order. It adds stock truth,
picking, delivery, technician execution, and warranty. The same request
rules as Phase 1 and 2 apply: routes check the caller and shape the
response, services hold the rules, `get_db` commits or rolls back, and
every state change writes an audit event.

## Flow

1. `confirm_order` (Phase 2) now also inserts one `reserved` stock
   reservation per material line, in the same transaction.
2. Warehouse receipts supplier goods with a stock operation:
   `draft` -> `ready` -> `done`. Only validation writes `stock_ledger`
   rows, in one transaction.
3. Picking is delivery creation: `POST /api/v1/deliveries` copies the
   order's material lines and refuses with `insufficient_stock` when
   on-hand minus other orders' reservations does not cover the pick.
4. The delivery moves `prepared` -> `in_transit` -> `delivered` ->
   `confirmed`. Confirmation consumes the reservations and activates a
   five-year warranty in the same transaction.
5. Sales sets a real slot on the scheduling request, gets ranked
   technicians (never an invented slot), and creates the installation
   job. The technician verifies the customer OTP, records evidence and
   signature, and completes the job.

## Stock truth

- `stock_ledger` is the only on-hand source. `GET /api/v1/stock`
  aggregates it. No cached quantity is stored anywhere else.
- Validation locks the operation row, then checks each line in a stable
  `(component, from, to)` order. A failed check raises before any
  ledger insert, so stock and the ledger stay unchanged.
- Two concurrent validations serialize on the row lock. The loser gets
  `invalid_transition`.
- Quantities are `NUMERIC(14, 4)`. Only adjustments accept negatives,
  and a negative adjustment that would drive stock below zero fails.
- Operation ids are idempotent per `(created_by, idempotency_key)`.
  The same key and body replays the operation; a different body gets
  `idempotency_conflict`.

## Reservations

- Created automatically at order confirmation, plus a manual
  `POST /api/v1/stock/reservations` for recovery. Unique per
  `(order, component)`; replays return the existing rows.
- States: `reserved` -> `consumed` (delivery confirmation) or
  `released` (future cancellation path). Delivery picking subtracts
  other orders' `reserved` quantities from on-hand.

## Serials and procurement

- `equipment_serials.serial_number` is globally unique, normalized to
  upper case. A second scan of the same serial gets `serial_exists`.
  A serial cannot join a validated (`done`) operation.
- Replenishment: warehouse proposes, only `warehouse_manager` or
  `admin` decides (`approve`/`reject`). Staff approval gets 403.
  Decided requests reject a second decision with `invalid_transition`.
  `threshold_suggestion` reports on-hand, reserved, available, and a
  suggested quantity without writing anything.

## Jobs and warranty

- Job states: `created` -> `scheduled` -> `en_route` -> `on_site` ->
  `completed`. Arrival uses the server clock. The customer OTP is a
  6-digit single-use challenge: hashed at rest, 30-minute expiry, five
  wrong attempts lock it. Completion requires OTP verified plus
  evidence (at least one photo ref) plus a customer-confirmed
  signature.
- The creation response returns the one-time `customer_code` (the demo
  channel, like the dev mailbox for email OTP). The technician reads
  it to the customer on site.
- Recommendations rank active technicians by open jobs and omit anyone
  with 5 or more. They never persist an assignment.
- Warranty activates only on delivery confirmation: `starts_at` is the
  confirmation time, five years long, status `active`. Only `support`
  or `admin` can void it.

## Files

| Path | Belongs there |
| --- | --- |
| `app/models/phase3.py` | Tables and check constraints |
| `app/schemas/phase3.py` | Pydantic input/output, `extra="forbid"` on writes |
| `app/services/inventory_service.py` | Operations, ledger, reservations, serials, replenishment |
| `app/services/fulfillment_service.py` | Deliveries, picking check, warranty |
| `app/services/installation_service.py` | Scheduling, recommendations, jobs, OTP |
| `app/api/v1/warehouse.py` | Stock, reservations, serials, replenishment, deliveries |
| `app/api/v1/installation.py` | Slots, recommendations, jobs, warranties |
| `alembic/versions/d5f1a2b3c4e5_*` | Phase 3 schema plus wider scheduling/preparation statuses |
| `tests/test_phase3_warehouse_installation.py` | Twelve PostgreSQL-backed tests |

## Status values opened by the migration

- `installation_scheduling_requests.status`: `unscheduled`,
  `scheduled`, `assigned`, `completed`, `cancelled` (was unscheduled
  only).
- `warehouse_preparation_requests.status`: `pending_preparation`,
  `picking`, `ready`, `delivered` (was pending only). The preparation
  queue itself is unchanged; the picking record is the delivery.

## What Phase 3 does not do

- No automatic purchase orders: an approved replenishment does not
  create a receipt operation by itself.
- No skill matrix: recommendations rank by open jobs only.
- No customer self-scheduling: only sales sets slots.
- No partial deliveries or returns: one delivery per order, forward
  only.
