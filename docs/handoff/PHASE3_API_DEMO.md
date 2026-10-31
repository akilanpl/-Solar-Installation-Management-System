# Phase 3 API demo instructions

Run the API against the local development database. The demo reuses the
Phase 2 seed: `make seed` provisions `EMP-WH-001` (warehouse) and
`EMP-WHM-001` (manager). Sign in as warehouse staff through
`POST /api/v1/auth/login` with `account_kind: employee`, keeping the
CSRF token and session cookie rules from Phase 1.

## 1. Receive stock

```http
POST /api/v1/stock/operations
Idempotency-Key: demo-receipt-001
{"operation_type": "receipt", "lines": [
  {"component_code": "PANEL-550", "quantity": "10.0000", "to_location": "MAIN"}]}
```

Then ready, then validate:

```http
POST /api/v1/stock/operations/{id}/ready
POST /api/v1/stock/operations/{id}/validate
GET /api/v1/stock
```

Expect `PANEL-550` on-hand `10.0000` at `MAIN`.

## 2. Fail a validation without side effects

Ready and validate a delivery of 999 panels. Expect 409
`insufficient_stock` and an unchanged `GET /api/v1/stock` total.

## 3. Pick a real order

With a confirmed Phase 2 order on screen:

```http
POST /api/v1/deliveries
Idempotency-Key: demo-delivery-001
{"order_id": "<order id>"}
GET /api/v1/stock/reservations?order_id=<order id>
```

Without received stock the pick fails with `insufficient_stock`.
After receiving the order's exact material quantities, the delivery is
`prepared` with one line per material.

## 4. Confirm and watch the warranty appear

```http
POST /api/v1/deliveries/{id}/transit
POST /api/v1/deliveries/{id}/deliver
POST /api/v1/deliveries/{id}/confirm
GET /api/v1/warranties/order/{order_id}
```

Expect the warranty `active` with a five-year span. Reservations for
the order are now `consumed`.

## 5. Run the job

```http
POST /api/v1/assignments/recommendations {"order_id": "<order id>"}
POST /api/v1/jobs {"order_id": "<order id>", "technician_user_id": "<tech id>"}
```

Keep the one-time `customer_code` from the response. As the assigned
technician: arrival, then `customer-otp` with the code, then `evidence`
(one photo ref minimum), then `signature` with
`"customer_confirmed": true`, then `completion`. Skipping any step
returns 409 naming the missing gate (`otp_required`,
`evidence_required`, or `signature_required`).

## 6. Show the guards

- A customer calling `POST /api/v1/stock/operations` gets 403.
- Warehouse staff calling a replenishment decision gets 403; the
  manager's approve returns `approved`.
- Scanning the same serial twice gets 409 `serial_exists`.
