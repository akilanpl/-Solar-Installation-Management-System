# Phase 4E — Architecture

Base SHA (verified): `26a5f129e1eeea5ad772ab4e1b8c5f8f6d43bc3d` — "4B checkpoint 6".
This checkpoint builds only on that 4B base. No 4C/4D code was read, merged or depended on.

## What was added

Three independent feature slices, all additive:

1. **Secure authentication** — WebAuthn passkeys (registration + assertion, server-verified
   with the maintained `webauthn` library), TOTP second factors (enrollment, verification,
   lockout, one-time recovery codes), login MFA tickets, and step-up grants for sensitive
   actions. Password login is unchanged for accounts without a verified factor.
2. **Offline-first technician sync** — an idempotent intake (`POST /offline/sync`) with
   per-operation idempotency keys, optimistic-lock `field_version` checks, conflict/reject
   verdicts, retry-safe evidence upload, and assignment scoping. The browser queue lives in
   IndexedDB (`src/lib/offlineQueue.ts`, swappable store, memory store for tests).
3. **Warranty extensions** — terms, versioned offers and a request lifecycle on top of the
   exact Phase 4B serial coverage/policy model. Extensions lengthen the 4B coverage row;
   the extension row snapshots the original end date, so 4B decisions keep pointing at
   unchanged snapshots. No invoice, ledger or payment logic: paid extensions wait in
   `pending_payment` until support records a verified real-world reference.

## New backend modules

| Area | Files |
|---|---|
| Data | `apps/api/app/models/phase4e.py` (10 new tables), `field_version` columns on `surveys` and `ticket_repair_jobs` |
| Migration | `apps/api/alembic/versions/35958a00676d_*.py` (head; descends from `4b1c2d3e4f51`) |
| Auth | `app/services/webauthn_service.py`, `app/services/mfa_service.py`, `app/api/v1/auth_extra.py` |
| Offline | `app/services/offline_sync_service.py`, `app/api/v1/offline.py` |
| Extensions | `app/services/warranty_extension_service.py`, `app/api/v1/warranty_extensions.py` |
| Schemas | `app/schemas/phase4e.py` (re-exported from `app/schemas/__init__.py`) |
| Config | 12 new `SOLAROPS_*` settings (RP ID/origins, challenge/ticket TTLs, TOTP, lockout, step-up) with production guards |

Shared-file edits are minimal and documented in `PHASE4E_PARALLEL_INTEGRATION_HANDOFF.md`:
login MFA branch, `create_session` helper, `job.field_version` bumps on diagnostics/work,
CORS `X-Strong-Auth` header, OpenAPI contract + generated types, migration-head test pin.

## New frontend modules

- `src/lib/webauthn.ts` — ceremony helpers (binary translation, discoverable-login support).
- `src/lib/offlineQueue.ts` — versioned queue, states, sync engine, per-user purge.
- `src/components/security.tsx` + `src/app/security/page.tsx` — passkeys, TOTP, recovery, sessions.
- `src/components/offline.tsx` + `src/app/technician/offline/page.tsx` — assignments, drafts, queue, evidence.
- `src/components/extensions.tsx` + customer/support pages — eligibility, requests, reviews.
- Login page: passkey button (flag-gated) and MFA-ticket second step; design unchanged otherwise.
- `src/lib/access.ts`: shared `/security` route for every authenticated role; nav entries added.

Feature flags: `NEXT_PUBLIC_SOLAROPS_PASSKEYS` and `NEXT_PUBLIC_SOLAROPS_OFFLINE`
(off unless `on`). No service worker: IndexedDB + online/offline detection covers the
workflow without stale-asset risk (see `PHASE4E_OFFLINE_SYNC.md`).

## Verification (detail in `PHASE4E_TEST_REPORT.md`)

- Backend: 236 passed (203 inherited + 33 new: 11 auth, 12 offline, 9 warranty). Ruff clean.
- Frontend: 18 vitest passed, typecheck, ESLint, production build clean.
- Browser acceptance (isolated stack, disposable `solarops_4e_preview` DB, ports 8015/3015,
  CDP virtual authenticator): 5 specs passed covering scenarios A–E.
