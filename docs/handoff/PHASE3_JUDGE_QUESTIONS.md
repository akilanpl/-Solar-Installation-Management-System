# Phase 3 technical judge handbook (42 questions)

Each answer states the behavior, the mechanism, the code reference, and
the honest limitation. All claims are proven by
`apps/api/tests/test_phase3_warehouse_installation.py` (21 tests) plus
the 46 Phase 1–2 tests, run against PostgreSQL.

## Stock truth and operations

### 1. Where is stock truth?
`stock_ledger` only. `GET /api/v1/stock` sums it per
component/location. No cached quantity exists anywhere else.
Ref: `inventory_service.stock_levels`. Limitation: no historical
as-of-date query; only current on-hand.

### 2. What changes stock?
Only `validate_operation` inserts ledger rows, plus the internal
delivery-pick and restock operations created by the delivery flow.
Ref: `inventory_service.validate_operation`,
`fulfillment_service._deduct_pick/_restock_cancelled_pick`.
Limitation: picks deduct from MAIN only (see Q10).

### 3. What happens when validation fails?
The check raises before any ledger insert, in the same request
transaction, so stock and the ledger stay unchanged.
Ref: `validate_operation` builds `deltas` before inserting.
Proven by `test_failed_transfer_and_delivery_leave_ledger_unchanged`.

### 4. What are the operation states?
`draft` -> `ready` -> `done`, with `cancelled` allowed before `done`.
Skipping a step returns 409 `invalid_transition`.
Proven by `test_draft_operation_cannot_validate_and_double_validate_fails`.

### 5. How are concurrent validations on one operation handled?
The operation row is locked (`SELECT ... FOR UPDATE`). The loser sees
status `done` and gets 409.
Proven by `test_concurrent_validation_has_a_single_winner`.

### 6. How are races across different operations handled?
`lock_components` locks the catalogue rows in sorted order before any
availability check, so two concurrent writers serialize per
component and the loser gets 409 `insufficient_stock`.
Ref: `inventory_service.lock_components`, called by
`validate_operation` and `_check_pick_availability`.
Proven by `test_concurrent_picks_serialize_on_component_locks`.

### 7. What numeric type holds stock?
`NUMERIC(14, 4)`, never float. Only adjustments accept negatives, and
a negative adjustment that would drive stock below zero fails.
Ref: `StockOperationLine.quantity`, `StockLedger.quantity_delta`.

### 8. How does idempotency work for operations?
Unique per `(created_by_user_id, idempotency_key)`. Same key and body
replays the operation; a different body returns 409
`idempotency_conflict`. Ref: `create_operation`.

## Reservations and picking

### 9. How does an order reserve stock without moving it?
`confirm_order` calls `reserve_for_order` in the same transaction,
writing one `reserved` row per material line.
Ref: `order_service.confirm_order`, `inventory_service.reserve_for_order`.
Proven by `test_confirmed_order_creates_reservations`.

### 10. From which location does picking deduct?
MAIN only. A delivery for stock sitting at SITE fails with 409 until a
`transfer` operation stages it to MAIN.
Proven by `test_site_stock_must_transfer_to_main_before_pick`.
Limitation: deliberate simplification; multi-location allocation
rules are not implemented.

### 11. Can two orders pick the same goods?
No. Creation checks MAIN on-hand under the component lock and deducts
it atomically with the delivery row. The second order gets 409 and no
delivery row or ledger row is created.
Proven by `test_competing_orders_cannot_pick_the_same_stock`,
which also asserts the loser's reservations stay `reserved`.

### 12. What does a failed delivery leave behind?
Nothing: no delivery row, no ledger rows, reservations untouched.
The availability check runs before any insert in the same
transaction. Proven by the atomicity asserts in
`test_warranty_void_guards_and_failed_pick_creates_nothing`.

### 13. When are reservations consumed?
At delivery confirmation, in the same transaction as the warranty
activation. Ref: `fulfillment_service.transition`, `consume_reservations`.
Proven by the `consumed` assert in the warranty test.

## Deliveries and warranty

### 14. What is the delivery state machine?
`prepared` -> `in_transit` -> `delivered` -> `confirmed`, with
`cancelled` from `prepared` or `in_transit`. Illegal jumps return 409.
Ref: `transition`. Proven by duplicate-confirm and cancel tests.

### 15. Can a delivery be confirmed twice?
No. The second confirm sees status `confirmed`, which has no outgoing
edge, and gets 409 `invalid_transition`.
Proven by `test_duplicate_delivery_confirmation_fails`.

### 16. What does cancelling do to stock?
It writes a compensating receipt (`+qty` to MAIN) through a done
stock operation in the same transaction, then flips the delivery to
`cancelled`. A cancelled delivery cannot move again.
Proven by `test_delivery_cancel_restocks_main`.

### 17. What activates the warranty?
Delivery confirmation only. `_activate_warranty` runs in the confirm
transaction: `starts_at` is the confirmation time, five years long,
status `active`. Ref: `fulfillment_service._activate_warranty`.

### 18. Who can void a warranty, and when?
Only `support` or `admin`, and only from `active`. Warehouse staff
gets 403; a second void gets 409.
Proven by `test_warranty_void_guards_and_failed_pick_creates_nothing`.

### 19. Is there one delivery and one warranty per order?
Yes. Both tables carry a unique constraint on `order_id`. A second
delivery attempt returns 409 `duplicate_delivery`.

## Serials and procurement

### 20. How are serials registered?
`POST /api/v1/serials/scan` stores the upper-cased serial globally
unique. A duplicate scan returns 409 `serial_exists`, and a serial
cannot join a validated operation.
Proven by `test_serial_scan_is_unique_and_rejects_done_operations`.

### 21. How is a serial assigned to an order?
`POST /api/v1/serials/{id}/assign` sets `order_id` and flips
`in_stock` to `reserved`. It rejects serials already assigned (409),
unknown orders (404), and components not on the order's BOM (409
`serial_component_mismatch`). Ref: `fulfillment_service.assign_serial`.

### 22. When does a serial become installed?
At delivery confirmation, `_install_assigned_serials` flips the
order's `reserved` serials to `installed` in the same transaction.
Proven by the end of `test_serial_assign_install_and_mismatch`.

### 23. Who can request replenishment?
Warehouse staff, manager, or admin. The request starts `proposed`.
Ref: `request_replenishment`.

### 24. Who can approve it?
Only `warehouse_manager` or `admin`. Staff approval returns 403, and
a decided request rejects a second decision with 409.
Proven by `test_replenishment_staff_cannot_approve`.

### 25. Does approval create stock?
No. An approved request is a decision record only; inbound stock
still arrives through an explicit receipt operation.
Limitation: no automatic purchase order or goods-receipt linkage.

## Scheduling and jobs

### 26. Who sets the installation slot?
Only sales or admin, via `POST /scheduling/installations/{id}/slot`.
The timestamp must carry a timezone. The slot is a real chosen time;
nothing invents one. Ref: `installation_service.schedule_slot`.

### 27. What do recommendations return?
Technicians ranked by open-job count, omitting anyone with 5 or more.
They never persist an assignment and never create a slot.
Ref: `recommend_technicians`.
Limitation: no skill matrix; ranking is by load only.

### 28. What are the job states?
`created` -> `scheduled` -> `en_route` -> `on_site` -> `completed`,
plus `cancelled`. Arrival uses the server clock.
Ref: `mark_arrival` uses `utcnow()`.

### 29. What gates job completion?
All three: verified customer OTP, recorded evidence (minimum one
photo ref), and a customer-confirmed signature. Each missing gate has
its own 409 (`otp_required`, `evidence_required`,
`signature_required`). Proven by `test_job_completion_requires_otp_evidence_and_signature`.

### 30. How does the customer OTP work?
A 6-digit single-use challenge, hashed at rest (`SHA-256`),
30-minute expiry, five wrong attempts lock it (`otp_locked`).
Expired codes return 409 `otp_expired`; reuse after success returns
409 `otp_missing` because the challenge is consumed.
Proven by `test_expired_and_reused_customer_otp_fail`.

### 31. How does the technician get the code?
The creation response returns the one-time `customer_code` (the demo
channel, like the dev mailbox for email OTP). The technician reads it
to the customer on site. Limitation: no SMS provider; the plaintext
exists only in that response.

### 32. Can a technician touch another technician's job?
No. Reads and writes for a foreign job return 404, and the
technician's own list contains only their jobs.
Proven by `test_foreign_technician_cannot_touch_assigned_job`.
This also fixed a real inconsistency found in audit: reads returned
403 (leaking existence) while writes returned 404.

## Security and roles

### 33. What can a customer not do in Phase 3?
Customers get 403 on stock, operations, and reservations, and 404 on
other customers' deliveries, jobs, and warranties.
Proven by `test_customer_cannot_touch_warehouse_and_scheduling_guards`.

### 34. What can warehouse staff not do?
Decide replenishment (403), schedule slots, create jobs, or void
warranties (403). They own stock, deliveries, serials, and picks.

### 35. What can a technician not do?
Confirm nothing except deliveries; create no jobs, slots, or
operations. They execute only their assigned jobs.

### 36. How are wrong state transitions reported?
Always 409 `invalid_transition`, never silent success. How are
forbidden roles reported? 403 `forbidden`, except customer access to
another customer's rows, which is 404 to avoid leaking existence.

## Integration and migrations

### 37. What did Phase 3 change in Phase 1–2 code?
One migration (new tables plus wider scheduling and preparation
statuses), one lazy import in `order_service.confirm_order` for
reservations, two routers on the existing CSRF-protected `api_router`,
and contract doc updates. No Phase 1 or 2 route, service, or
migration was edited. All 46 pre-existing tests still pass.

### 38. How were migrations verified?
Alembic `upgrade head` from an empty `solarops_fresh` database
applied all four revisions; `downgrade -1` plus `upgrade head`
round-tripped; seeds held 7 roles, 12 packages, 2 locations. The
fresh database was dropped afterwards; `solarops` and
`solarops_test` were never touched by this check.

### 39. What is the end-to-end proof?
`test_cross_phase_order_to_completed_installation` drives
enquiry -> survey -> quotation -> cash payment -> order ->
reservation -> receipt -> delivery -> warranty -> slot -> job ->
completion through authenticated HTTP, asserting ledger, warranty,
and job rows in PostgreSQL.

### 40. What remains NOT IMPLEMENTED?
Replenishment auto-receiving, skill-based recommendations,
dispatcher overrides, customer self-scheduling, partial deliveries
and returns, multi-location pick allocation, and serial-level
picking (serials attach to orders, not to delivery lines).

### 41. What has only PARTIAL coverage?
Threshold suggestions (`threshold_suggestion` has no dedicated test;
covered indirectly via ledger math), the delivery list filters for
every role (owner-customer path tested, staff paths exercised),
and idempotent replays of delivery creation (duplicate-order path
tested, same-key replay returns the original).

### 42. What is the readiness verdict?
Backend VERIFIED for the acceptance scope: 67 of 67 tests pass,
lint clean, contract regenerated from the app, migrations proven on
a disposable database. Frontend screens (teammate 2) and
independent QA (teammate 3) remain, and the Q40 limitations above
are the explicit Phase 4 candidates. No Phase 4 work was started.
