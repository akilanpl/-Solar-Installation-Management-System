# Phase 2 sales workflow

This is the path from a qualified enquiry to a confirmed installation order. The functions below are the ones to walk in a review. HTTP handlers only check the caller and shape the response. `get_db` commits the session if the handler returns and rolls it back if anything raises.

## Qualification

`qualify_enquiry` still uses `submitted`, `under_review`, `qualified`, and `not_qualified`. Moving to `qualified` requires `shadow_free_area_sqm` and `grid_connection_suitable`, and it records `decision_by_user_id` and `decision_at`.

`approved_survey_exists` blocks a later change to those two fields with `qualification_locked`. Sending `acknowledge_downstream: true` writes the enquiry and an audit event whose metadata says downstream records were not rewritten. Survey rows, quotation lines, and orders are not updated by that call.

## Survey

`survey_service` checks every transition. `create_survey` refuses an enquiry that is not `qualified`. `submit_survey` refuses every user except the assigned technician. `decide_survey` is sales or admin, and it writes `survey_status_history` plus `audit_events` before the request commits.

Measurements are `Numeric`, not floats: azimuth 0–360 degrees, tilt 0–90 degrees, area in square metres, cable distance in metres, at most two decimal places. Evidence bytes are sniffed for JPEG, PNG, WebP, or PDF and stored under `var/survey-evidence` with a generated key. The database stores that key, not the client's path.

`resurvey` inserts a new draft. The rejected survey stays rejected.

Assignment does not invent a time. `appointment_status` is `pending` until the request includes `appointment_starts_at`.

## BOM

`app/domain/catalogue.py` seeds version 1 of each package. A system package has two 550 W panel lines per kilowatt, an inverter, stands, two wiring bundles, connectors, a switch, a distribution box, earthing, and installation. Off-grid templates add one 1 kWh battery per kilowatt and one charge controller. Those quantities are the template, not a guess at the site.

`apply_cable_adjustment` is the only measurement change. The template covers 25 metres. Each further 10 metres, rounded up, adds one wiring bundle at the template's own unit price. A template with no wiring line is left unchanged.

`issue` in `quotation_service` copies the current template version id and the adjusted lines onto the quotation. Editing the catalogue later means inserting another `package_template_versions` row. Old quotations keep the version they stored.

## Pricing

Money is integer paise. `price_quote` adds material and installation customer prices, subtracts an optional discount of at most 10 percent, then applies `SOLAROPS_GST_RATE_BPS`. The default 1800 is a demonstration rate, not a statutory claim. Tax is `(taxable * bps + 5000) // 10000`. The quotation header has a check constraint that `total_minor` equals materials plus installation minus discount plus tax. The client cannot send a total.

Material cost on each line is 70 percent of the demonstration customer price, rounded down, and is stored so the quote can show cost and price separately.

A payment requirement is created with the quote. The advance is `SOLAROPS_ADVANCE_PERCENT` (default 40) of the total, stored on the requirement so a later settings change does not rewrite it.

## Revisions and acceptance

An enquiry has at most one `issued` or `accepted` quotation. `uq_quotations_one_active` enforces that. `create_quotation` and `revise_quotation` lock the enquiry row first, so two concurrent issues cannot both pass. A second issue returns `quotation_already_open`. A revision marks the current row `superseded` and flushes that change before inserting the replacement, still inside the same transaction. `quotation_lines` on the old row are not updated. Withdrawing a quotation leaves the enquiry free for a new issue.

`accept_quotation` locks the row, checks the customer, the `issued` status, the expiry, and the approved survey, then inserts `quotation_acceptances` with the quotation id as the primary key. A second accept gets `already_accepted`.

Verified payments stay on the quotation they were paid against. The balance for a quotation includes verified payments on the revisions it superseded, each payment once. A revision therefore does not drop money already received and does not allow that same amount to be collected again. `outstanding_minor` is never negative. Payment verification locks the enquiry before it decides the outcome, so two full payments cannot both become verified.

`confirm_order` locks the enquiry, then the quotation. `uq_sales_orders_enquiry` allows one confirmed order for that enquiry. Repeating the same idempotency key returns the original order and does not create a second warehouse or scheduling request. The handoff rows are still inserted in the order transaction.

## Payments

`create_sandbox_intent` inserts `pending` with `is_test_only` true and `provider` `sandbox`. It is refused when `SOLAROPS_APP_ENV` is `production`. `apply_sandbox_outcome` moves the row through `processing` to `verified`, `failed`, or `unresolved`. `unknown` is `unresolved` and does not count toward the advance. `record_cash_receipt` is the manual path: sales or admin, a receipt reference, `is_test_only` false, status `verified`. There is no endpoint that verifies a payment from a screenshot or a customer-typed reference alone. Card numbers, CVVs, and banking credentials are not fields.

The same idempotency key and body returns the original intent. A different body returns `idempotency_conflict`.

## Order and handoff

`confirm_order` locks the quotation. It requires `accepted`, an approved survey, and verified payments at least equal to the stored advance. If any counted payment is test-only, the order's `payment_verification_state` is `test_verified` and `test_only_payment` is true. A cash-only confirmation is `manually_verified`.

In that same transaction it inserts `sales_orders`, `sales_order_lines` (the frozen BOM and tax lines), `warehouse_preparation_requests` with material quantities, and `installation_scheduling_requests` with `slot_starts_at` null and status `unscheduled`. Nothing updates a stock ledger. `uq_sales_orders_quotation` prevents a second order. Repeating the confirming user's idempotency key returns the first order. A failed request rolls back the order and both handoff rows together because they share the request transaction.

Warehouse staff can read the preparation queue. Sales and admin can read the scheduling queue. Neither queue dispatches or installs anything.

## Roles

Customers see their own enquiries, surveys, quotations, payments, and orders. Another customer's ids return 404. Technicians can submit only the survey assigned to them. Sales and admin run qualification, survey review, quotations, cash receipts, and order confirmation. Warehouse roles see preparation and orders, not the scheduling queue. A role that cannot use a route gets 403.

## Contracts

Implemented routes are in `docs/api/API_CONTRACTS.md` and in `contracts/generated/openapi.json`. `apps/web/src/generated/schema.ts` is generated from that file. Regenerate both after a route change. Do not edit the TypeScript by hand. UPI, cards, wallets, net banking, EMI, invoices, refunds, and stock operations remain planned.
