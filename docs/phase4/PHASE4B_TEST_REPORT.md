# Phase 4B Test Report

HEAD: `5bf3680`. Disposable DBs: `solarops_release_test_20261102` (pytest),
`solarops_4b_preview` (browser). Ports: API `8012`, web `3012` (both confirmed
free before use; Playwright owns the servers per run).

## Results

- Backend full suite: **203 passed** (179 inherited Phase 1–3 + 4A, 24 Phase 4B:
  8 warranty, 5 replacement, 11 billing). Command uses
  `SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME` + `SOLAROPS_TEST_DATABASE_URL`;
  other databases were never touched.
- Ruff (`app tests scripts`): clean. Frontend: typecheck clean, lint clean,
  12/12 unit tests pass (incl. new INR paise formatter), production build passes.
- OpenAPI regen + `generate:api`: zero diff — committed contracts match the app.
- Migration proof: `test_migrated_schema_matches_current_sqlalchemy_metadata`
  failed on index-name drift (migration used shortened names, models use
  defaults); fixed by additive migration `4b1c2d3e4f51`, now green. The
  round-trip test's stale 4A head pin was updated to the 4B head with the
  4B tables added to its presence check. No test was weakened: both assert
  more than before.

## Browser acceptance (`playwright.4b.config.ts`, 3/3 passed)

1. Covered inverter fault → decision `covered`, estimate payable ₹0.00,
   customer accepts exact version, invoice `outstanding`, warehouse
   consumption recorded, resolution confirmed, ticket closed, fresh login
   sees closed history + covered verdict.
2. Expired warranty (future evaluation date) → `not_covered`, full-price
   math verified part-by-part, customer rejection blocks invoicing (409),
   version 2 accepted and billed exactly, closed and persisted.
3. Replacement → approve → reserve → issue → technician install (assignment
   enforced: unassigned install is rejected) → quarantine inspection;
   old unit `quarantined`, new unit linked to customer with transferred cover.

Incidental UI fix during acceptance: duplicate "Serial number" labels on the
support warranty page were disambiguated.

## Gaps

- `seeded.spec.ts` still needs `var/demo-credentials.json` (pre-existing,
  untouched). The 4B suite signs up fresh customers instead.
- No external manufacturer provider; no payment provider (by design).
