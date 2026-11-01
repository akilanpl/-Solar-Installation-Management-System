# Phase 4B Warranty Policy — Serial-Level Coverage

## Activation

Coverage activates only from a valid confirmed delivery event for the exact
serial (`POST /api/v1/warranty/orders/{order_id}/activate-coverages`).
No confirmed delivery means no delivery-based warranty. Activation records
the delivery reference, the effective policy version, and start/end dates.

## Decisions

`POST /api/v1/warranty/coverage-decisions` evaluates customer, serial,
reported fault, evaluation timestamp, policy version, exclusions, and prior
replacements/exceptions, returning `covered`, `not_covered`,
`pending_verification`, or `blocked` with the supporting rule and reason.
Date-range membership alone never implies coverage: exclusions, fault
categories, and missing evidence can still deny or block. Repeat decisions
replay idempotently; decisions with an exception carry the exception in the
repeat key so an approved override is never silently re-decided.

## Versions and history

Policy edits publish new versions; every decision and coverage row freezes
the version it used. Boundary, expiry (via evaluation timestamp), exclusion,
conflict, and supersession cases are covered by 8 backend tests plus the
expired-warranty browser scenario.

## Replacement continuation

Replacement carries the remainder of the original cover by default, or a
policy-limited fixed extension when the version allows it. Manufacturer
authorization is modelled as pending/blocked until real evidence arrives;
it is never invented.
