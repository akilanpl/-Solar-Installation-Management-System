# Phase 4E — Test Report

Base SHA: `26a5f129e1eeea5ad772ab4e1b8c5f8f6d43bc3d` (Phase 4B checkpoint 6).
Final HEAD: see handoff (backend `afa0300` + frontend commit + docs commit).

## Baselines (E0, disposable `solarops_release_test_20261104`)

- Backend: 191 passed. Frontend: 12 passed. Typecheck clean.

## Final gates (all on current code)

| Layer | Result |
|---|---|
| Backend `pytest` (isolated disposable DB) | **236 passed** — 203 inherited + 33 new |
| Backend `ruff check app tests scripts` | clean |
| Frontend `vitest` | **18 passed** (12 inherited + 6 offline-queue) |
| Frontend `tsc --noEmit` | clean |
| Frontend ESLint | clean |
| Production `next build` | clean, all 4 new routes render |
| OpenAPI contract test | passes against regenerated `contracts/generated/openapi.json` |
| Migration round-trip test | passes (head pin updated to `35958a00676d`; see handoff) |

### New backend tests (33)

- `test_phase4e_auth.py` (12): registration, scoped/discoverable login, invalid
  origin/RP, expiry, replay, revocation, cross-account use, TOTP enroll/confirm,
  202 ticket login, wrong codes, lockout, recovery login + session revocation,
  rate limiting, revocation re-auth, role preservation, TOTP + passkey step-up grants.
  WebAuthn uses a test virtual authenticator minting real ES256 keys/signatures;
  the server still verifies through the maintained library.
- `test_phase4e_offline.py` (12): draft apply + idempotent replay, stale-version
  conflict (offline and online origins), submitted-state rejection, measurement
  field gating, diagnostics/work/checklist sync, mixed batch verdicts, forbidden
  actions, user isolation, evidence retry + tamper conflict, unauthenticated rejection.
- `test_phase4e_warranty.py` (9): paid lifecycle to `active` with verified reference,
  free auto-activation, idempotent requests, category/window/void ineligibility,
  serial-ownership isolation, grant enforcement, stale-offer blocking, audit/history
  preservation.

## Browser acceptance (E7, isolated stack)

Disposable `solarops_4e_preview` DB, API on 8015, Next on 3015 (both verified free),
Playwright-owned servers, CDP virtual authenticator, `workers: 1` (shared preview
staff). **5 specs passed**:

- A (passkey): signup → password login → register → logout → passkey login →
  own-records-only → revoke → revoked credential rejected (401 logged).
- B (MFA/recovery): enroll → ticket login → wrong-code rejection → TOTP login →
  recovery codes → recovery login without privilege change → revocation restores
  direct login.
- C (offline): assignments → sync measurement → applied + version bump + DB row;
  replay returns stored verdict.
- D (conflict/expiry): stale version conflicts; logged-out sync → 401 (client maps
  to `auth_required`, never fake success).
- E (warranty): policy → installed order → coverage → terms → eligibility → request →
  approval (coverage end unchanged) → verified-payment activation (end extended) →
  duplicate request rejected; PostgreSQL spot-checks after each transition.

## Security findings (all fixed, tests added)

1. MFA failure bookkeeping rolled back with the request — lockouts never persisted.
   Fixed with dedicated security transactions.
2. Discoverable login sent `allowCredentials: []` (forbids all credentials). Fixed.
3. Registration omitted resident-key request; step-up tickets ignored passkeys. Fixed.
4. Chromium rejects IP-literal RP IDs: acceptance uses `localhost`; production needs
   a real RP ID + HTTPS origins (enforced by config validation).

## Not claimed

- Production readiness (local acceptance only; real origins, HSM-backed keys, SMS/email
  deliverability, and load testing are out of scope).
- Service-worker offline shell (deliberately not built; rationale in offline doc).
- Phase 4A/4B regression beyond the inherited suites (all green, unmodified behavior).
