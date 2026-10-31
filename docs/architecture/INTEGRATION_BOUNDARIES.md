# Integration boundaries

Phase 1 does not call a payment gateway, weather service, or model API. `app/services/future_boundaries.py` defines the protocols and `registered_providers()` returns `{}`. A caller cannot receive a successful fake reading.

## SysCache (planned)

Support needs a single snapshot: identity, installations, open requests, serials, warranty, recent tickets, repair status, and the next action. PostgreSQL is the source. A later cache may store:

- `customer_id`
- `version`, a hash of the maximum `updated_at` of the source rows
- `generated_at`
- the snapshot body

Invalidation: any committed write to those source rows changes the version. Readers compare the version they were given. If the cache is missing or the version mismatches, read the database and return that. Authorization: support and admin may read any customer; a customer may read only their own id. Phase 1 has no cache and no timing claim.

## Technician assignment (planned)

Inputs: required skills, technician skills, site coordinates, a real schedule of open slots, jobs already assigned that day, and a maximum jobs per day. Output: ranked candidates with a reason, or an empty list. A technician without the required skill is excluded even if they are nearest. The algorithm must not create a slot that is not already in the schedule. A dispatcher can override and that override is an audit event. No endpoint assigns work in Phase 1.

## StockSense and replenishment (planned)

StockSense (`https://github.com/akilanpl/StockSense`) is a Next.js and Prisma inventory app. SolarOps does not port that TypeScript. The rules worth keeping, from its README and schema comments, are:

- Receipts, transfers, deliveries, and counts use Draft, then Ready, then Done. Cancellation is allowed before Done.
- Stock and the movement ledger change only when the operation is validated, in one transaction.
- A failed delivery leaves stock and the ledger unchanged.
- The validator locks the operation, then product/location pairs in a stable order.
- Quantities use a precise decimal (StockSense uses four decimal places). SolarOps will use `NUMERIC`, not float. Serialised solar equipment is an additional SolarOps table StockSense does not have.
- StockSense does not include reservations, costing, or automatic purchasing. SolarOps replenishment is a separate request: suggested quantity at a reorder threshold, then an approval by `warehouse_manager`. `warehouse_staff` can move stock later but cannot approve the request.

## Weather (planned)

`WeatherProvider.fetch` will return either an observation or a forecast, with `source` and the time it applies to. Observations and forecasts stay in different rows. The provider is not registered. Nothing in the API invents irradiance or predicts an equipment failure.

## Complaint summaries (planned)

A summariser may propose a category and priority. The ticket stores the original text and, separately, a suggestion that remains unconfirmed until a customer or support user accepts or edits it. Unconfirmed text is not the issue of record.

## Payments and energy (planned)

`PaymentProvider.create_intent` is not implemented. There is no route that returns a paid status.

Generation estimates, when added, need an assumptions record (location, capacity, performance ratio, weather source). Sensor measurements, if a meter exists, are a different field. Phase 1 has neither.

## Email

`build_email_sender` picks SMTP if `SOLAROPS_SMTP_HOST` is set, the file mailbox in development, or a capturing sender in tests. Production without SMTP raises `email_not_configured` instead of reporting that mail was sent.
