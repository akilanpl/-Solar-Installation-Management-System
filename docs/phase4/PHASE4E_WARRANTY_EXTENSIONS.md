# Phase 4E — Warranty Extensions

Built strictly on the Phase 4B serial policy model. No parallel warranty system exists:
eligibility reads `SerializedAssetCoverage` + its `WarrantyPolicyVersion` (the same
rows coverage decisions snapshot), and activation extends that coverage row's
`ends_at`. The `warranty_extensions` row snapshots `original_ends_at`, so prior
decisions keep pointing at unchanged history (asserted: decision count unchanged).

## Business policy is data, not constants

`warranty_extension_terms` (per policy, versioned, one active row) holds:
`extension_days`, `price_minor`, `currency`, `window_days` (covers active cover plus a
configurable grace period — the "90 days" from the brief is entered here, not in
code), `eligible_categories`, `max_extensions`, `requires_approval`.

## Lifecycle

`requested` → `pending_approval` → `pending_payment` → `active`, with `rejected`,
`cancelled`, `expired` terminals. Auto-advance: no-approval + free → `active`;
no-approval + paid → `pending_payment`. Every transition is validated and audited
(`warranty.extension_requested/pending_approval/pending_payment/approved/rejected/
cancelled/payment_verified/activated`).

## Offer contract (Phase 4C seam)

`warranty_extension_offers` are versioned per coverage: offer id + version, customer,
serial, exact price, source policy version, payment requirement, expiry (30 days).
`request.offer_version` binds the price; activation fails closed on superseded/expired
offers (`stale_offer` / `offer_expired`). Duplicate requests return the existing row
via `idempotency_key`. Phase 4C can consume offers as the payment source of truth;
nothing here settles money.

## Activation rules

- Never from a browser-only event. Paid extensions wait in `pending_payment` until
  support records a verified real-world reference (`record_payment_and_activate`).
- Free extensions activate on approval (or immediately when approval is not required).
- Approval, rejection review, terms management and activation require a fresh step-up
  grant; rejection needs a note; customers can only cancel non-terminal requests.
- Eligibility: customer-owned serial, live coverage, active terms, eligible category,
  no excluded component, open window, no live extension, under the maximum count.

## Frontend

- Customer: serial eligibility check with exact price/days/policy/version, request
  button, request list with statuses and decision notes.
- Support/admin: request review (approve/reject with step-up), payment verification
  with reference, terms visibility. Policy editing itself stays in the existing
  admin API.

## Out of scope (noted for Phase 5)

Automatic expiry sweeps (offers expire lazily on read; requests never time out),
invoice linkage beyond the offer contract, and multi-extension pricing tiers.
