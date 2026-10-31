# Phase 3 technical judge questions

Short answers a judge can verify against the code and the test suite.

## 1. Where is stock truth, and what happens when validation fails?

`stock_ledger` only. `GET /api/v1/stock` sums it. `validate_operation`
in `app/services/inventory_service.py` checks every line before
inserting any ledger row, in one request transaction, so a failure
leaves stock and the ledger unchanged. Proven by
`test_failed_transfer_and_delivery_leave_ledger_unchanged`.

## 2. How do concurrent validations avoid double stock movement?

The validator locks the operation row (`SELECT ... FOR UPDATE`) and
checks lines in a stable order. The second concurrent validation sees
status `done` and gets 409 `invalid_transition`. Proven by
`test_concurrent_validation_has_a_single_winner`.

## 3. How does an order reserve stock without moving it?

`confirm_order` calls `reserve_for_order` in the same transaction that
creates the order, writing one `reserved` row per material line.
Delivery picking subtracts other orders' reservations from on-hand;
delivery confirmation flips them to `consumed`. Proven by
`test_confirmed_order_creates_reservations` and the consumption assert
in the warranty test.

## 4. What stops picking stock that is not there?

`_check_pick_availability` in `fulfillment_service.py` requires
on-hand minus other orders' reservations to cover each material line.
Otherwise 409 `insufficient_stock` and no delivery row. Proven by
`test_picking_without_stock_fails`. This was a defect found during
Phase 3 testing: deliveries initially skipped the availability check.

## 5. What activates the warranty, and who can void it?

Delivery confirmation only. `_activate_warranty` runs in the same
transaction as the `confirmed` flip. Only `support` or `admin` can
void. Proven by `test_delivery_confirm_activates_warranty_and_blocks_replay`.

## 6. What gates job completion?

OTP verified (single-use 6-digit challenge, hashed, 30-minute expiry,
five-attempt lock) plus evidence (minimum one photo ref) plus a
customer-confirmed signature. Each missing gate returns its own 409.
Proven by `test_job_completion_requires_otp_evidence_and_signature`.

## 7. What can each role not do?

Customers get 403 on stock, reservations, and operation writes, and
404 on other customers' deliveries and jobs. Warehouse staff gets 403
on replenishment decisions. Technicians can only touch their assigned
jobs (others get 404). Proven by the security test and role asserts
across the suite.

## 8. What did Phase 3 change in Phase 1 and 2 code?

One migration (new tables plus wider scheduling and preparation
statuses), one lazy import in `order_service.confirm_order` for
reservations, two new routers registered on the existing
CSRF-protected `api_router`, and contract doc updates. No Phase 1 or 2
route, service, or migration was edited. All 46 pre-existing tests
still pass.
