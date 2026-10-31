# Phase 4B Architecture — Warranty Intelligence, Repair & Billing

Branch: `feature/phase4b-warranty-repair` (provisional stacked branch, local only).
Base: Phase 4A checkpoint `adc2166`. HEAD: `5bf3680`.
Migrations: `f4a7b2c1d093` (4A) → `4b1c2d3e4f50` (4B domain) → `4b1c2d3e4f51` (index alignment).

## Design

Phase 4B is additive. It reuses Phase 4A service tickets, ticket repair jobs,
and the Phase 3 warehouse ledger, delivery, and serial models. No 4A/Phase 1–3
table was altered except `equipment_serials`, whose status check constraint now
also admits `returned` and `quarantined`.

New domain tables (`app/models/warranty.py`):

- `warranty_policies` + `warranty_policy_versions` — versioned cover rules
  (duration, fault categories, components, exclusions, labour flag,
  replacement continuation). Example 2-year/20-year durations are data
  entered through the admin API, never code constants.
- `serialized_asset_coverage` — one row per installed unit: serial, order,
  customer, confirmed delivery reference, activation, start/end, policy
  snapshot, status (`active`, `expired`, `void`, `superseded`).
- `coverage_decisions` — frozen verdict + policy/coverage snapshots +
  repeat key, so later policy edits never rewrite history.
- `warranty_exceptions` — approved overrides with recorded reason.
- `service_price_books`, `service_tax_policies` — versioned approved pricing.
- `service_estimates`, `estimate_decisions` — versioned estimates; edits
  supersede, accepted versions freeze.
- `service_invoices`, `service_credit_notes` — immutable invoices
  (`outstanding`/`pending_payment`/`credited` only); adjustments are new
  credit-note rows. No general ledger: Phase 4C owns company accounting.
- `replacement_decisions`, `return_inspections` — one replacement serial per
  customer, warehouse custody chain, quarantine/restock/scrap verdicts.

## Money

Integer INR paise everywhere. Labour prorates per minute rounded half up;
tax applies to the customer-payable subtotal rounded half up. Covered lines
contribute zero to the payable amount; mixed estimates keep covered and
payable portions on separate lines.

## Status

VERIFIED: backend domain, migration ancestry to `4b1c2d3e4f51`, full suite
(203 passed), browser acceptance (3/3). PARTIAL: nothing outstanding in
scope. NOT IMPLEMENTED: real payment settlement, manufacturer provider
integration (`pending_manufacturer` stays blocked until evidence).
