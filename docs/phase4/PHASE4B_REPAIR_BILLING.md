# Phase 4B Repair & Billing

## Covered repair

Support reviews the frozen coverage decision, links/creates the repair job,
the technician records diagnostics, parts, work time, evidence, and a
completion summary. Estimates price covered lines at zero payable; uncovered
extras stay separately identified and need approval.

## Out-of-warranty repair

The application builds a versioned itemized estimate (ticket + repair
reference, customer/site, SKU lines, quantities, price-book version, paise
unit prices, labour rate/minutes, approved tax, covered vs payable split,
validity). The customer accepts or rejects the exact version. Rejection
authorizes nothing: invoicing a rejected estimate returns 409. A rebuild
supersedes (new version); accepted versions never mutate.

## Replacement

`proposed → approved/pending_manufacturer → reserved → issued → installed`,
plus `cancelled`. The proposal names the defective and replacement serials
up front, so one serial can never serve two customers. Reserve/issue run
real validated ledger operations; the old unit returns to `returned`, then
quarantine/restock/scrap via inspection with a recorded note. A technician
can confirm installation only while holding a repair job on the ticket.
Warranty transfers remainder by default per policy.

## Billing

Invoices derive from accepted estimates only, are immutable, and stay
`outstanding`/`pending_payment` without a real payment provider — no click
or mock marks them paid. Warehouse consumption posts a real ledger
adjustment linked to the invoice. Credit notes adjust the running total
against the immutable original. Retries replay by idempotency key; concurrent
invoice creation has a single winner (11 backend billing tests).
