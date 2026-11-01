# Phase 4E — Parallel Integration Handoff

Branch: `feature/phase4e-enhancements` (local only; never pushed, no merges).
Base: `26a5f129e1eeea5ad772ab4e1b8c5f8f6d43bc3d` (verified Phase 4B checkpoint).

## What the integrator needs to know

- **Migration head**: `35958a00676d` descends from `4b1c2d3e4f51`. If 4C/4D add heads
  on the same base, merge with `alembic merge` — do not rewrite history. Table names
  are 4E-unique (`webauthn_*`, `mfa_*`, `strong_auth_grants`,
  `technician_sync_operations`, `warranty_extension_*`); no 4C finance or 4D support
  names were touched or duplicated.
- **4C seam**: `warranty_extension_offers` is the purchase contract (offer id/version,
  customer, serial, agreed price, policy source, payment requirement). Paid extensions
  wait in `pending_payment`; 4C can reconcile invoices against it. 4E settles no money.
- **4D seam**: none (auth/offline/extensions do not overlap support, cache, weather or
  generation features). The only shared touchpoint is the login page, which keeps its
  existing flow plus additive passkey/MFA steps.

## Shared-file changes (all additive, backward compatible)

| File | Change |
|---|---|
| `app/api/v1/auth.py` | 202 ticket branch when a verified factor exists; `response_model` unchanged otherwise |
| `app/api/v1/router.py` | three new router registrations |
| `app/core/config.py` | 12 new settings + production RP/origin guards |
| `app/main.py` | CORS `X-Strong-Auth` header |
| `app/models/__init__.py`, `app/schemas/__init__.py` | re-exports of new modules |
| `app/models/workflow.py`, `app/models/support.py` | `field_version` columns (default 0, unread by old code) |
| `app/services/auth_service.py` | `create_session` helper; authenticate returns `(user, None)` when MFA is required |
| `app/services/ticket_service.py` | `field_version += 1` in diagnostics/work (shared optimistic locking) |
| `app/schemas/phase4e.py` (new) | `MfaStatusResponse.totp_factor_id` added for factor revocation UI |
| `tests/test_phase3_migrations.py` | head pin `4b1c2d3e4f51` → `35958a00676d` (tracks newest migration; substance unchanged) |
| `contracts/generated/openapi.json`, `web/src/generated/schema.ts` | regenerated (do not hand-edit) |
| `web/src/lib/access.ts` | shared `/security` route for all roles |
| `web/src/components/shell.tsx` | nav entries (Security, Offline field work, Warranty extensions, Extension reviews) |
| `web/src/app/{login,signup,verify-email}/page.tsx` | MFA step, passkey button, hydration markers (test-only `data-*`) |

## Potential conflicts with 4C/4D

- Sibling Alembic heads → `alembic merge`, then re-run `test_migrated_schema_matches_current_sqlalchemy_metadata`.
- If 4C also edits `auth.py`, `router.py`, `main.py` CORS or the OpenAPI contract,
  keep both additions; regenerate contracts once after merging.
- If 4D touches the login page or shell nav, preserve both link sets.

## Recommended reconciliation order

1. Merge 4C finance first (ledger/subledger constraints are load-bearing).
2. Merge 4D support features.
3. Merge 4E last (purely additive; re-run `make test` + contract regen after each merge).
4. Retire the disposable databases (`solarops_release_test_20261104`,
   `solarops_4e_preview`); they contain only test/preview data.

## Environment notes (not committed)

- Preview staff (`admin4e@`/`tech4e@`/`support4e@`/`sales4e@`/`wh4e@sunpower.example`)
  and the admin TOTP secret file `/tmp/solarops-4e-admin-totp.txt` exist only in the
  disposable preview DB / /tmp. Nothing production-like was created.
- Acceptance flags `NEXT_PUBLIC_SOLAROPS_PASSKEYS` / `NEXT_PUBLIC_SOLAROPS_OFFLINE`
  default off; production needs explicit `SOLAROPS_WEBAUTHN_RP_ID` + HTTPS origins.

## Status

IMPLEMENTED + VERIFIED: E1–E5 backend/frontend, 33 backend tests, 6 frontend tests,
full gates, 5 browser acceptance specs. PARTIAL: none. BLOCKED: nothing in scope.
Production hardening and 4C/4D integration remain for Phase 5.
