# Phase 4B API Contracts

Generated, never hand-edited: `contracts/generated/openapi.json` and
`apps/web/src/generated/schema.ts` (exported via `scripts/export_openapi.py`
+ `npm run generate:api`; regen verified with zero diff at HEAD).

## Warranty (`/api/v1/warranty`)

- `POST /policies`, `GET /policies` — admin policy publishing/listing.
- `POST /policies/{id}/versions`, `GET /policies/{id}/versions`.
- `POST /orders/{order_id}/activate-coverages` — support, from confirmed delivery.
- `POST /coverage-decisions` (Idempotency-Key) — support verdicts.
- `GET /coverage-decisions?ticket_id=` — ticket decision history.
- `GET /serials/mine` — customer own coverages.
- `GET /serials/lookup?serial_number=` — support exact-unit lookup.
- `POST /exceptions` — approved overrides with reason ≥ 10 chars.
- `POST /coverages/{id}/void` — support void with reason.

## Replacements (`/api/v1/replacements`)

- `POST /` (Idempotency-Key) `{ticket_id, old_serial_number, new_serial_number}`.
- `GET /` (customers auto-scoped; `?ticket_id=` filter), `GET /{id}`.
- `POST /{id}/approve`, `/manufacturer-auth {evidence_ref}`, `/reserve`,
  `/issue` (Idempotency-Key), `/install` (no body), `/inspect
  {verdict: quarantined|restocked|scrapped, note ≥ 10}`, `/cancel {reason}`.

## Billing (`/api/v1`)

- `POST /service-price-books {label, labour_rates, part_prices, effective_from}` (admin).
- `POST /service-tax-policies {label, rate_bps, effective_from}` (admin).
- `POST /tickets/{id}/estimates` (Idempotency-Key; needs final decision +
  submitted job with parts/time), `GET /tickets/{id}/estimates`.
- `GET /estimates/{id}`, `POST /estimates/{id}/decision
  {decision, estimate_version, note?}` (customer; exact-version match).
- `POST /service-invoices {estimate_id}` (Idempotency-Key; accepted only),
  `GET /service-invoices[?ticket_id=]`, `GET /service-invoices/{id}`.
- `POST /service-invoices/{id}/consume` (warehouse; real ledger adjustment).
- `POST /service-invoices/{id}/credit-notes {amount_minor > 0, reason ≥ 10}`,
  `GET .../credit-notes`.

## Frontend routes (16)

Customer: `/equipment`, `/estimates`, `/estimates/[id]`, `/bills`,
`/bills/[id]`, `/replacements`. Support: `/warranty`, `/estimates`,
`/estimates/[id]`, `/replacements`, `/replacements/[id]`, `/billing`.
Warehouse: `/replacements`, `/replacements/[id]`. Technician: `/install`.
Admin: `/pricing`. All inherit workspace role gates; no fake records,
no mock paid states; unavailable provider capabilities show as pending.
