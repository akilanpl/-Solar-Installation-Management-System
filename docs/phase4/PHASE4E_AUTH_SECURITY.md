# Phase 4E — Authentication & Security

## Passkeys (WebAuthn)

- Server verification uses the maintained `webauthn` (py-webauthn 3.0.1) library only.
  No attestation/assertion cryptography is implemented by hand; private key material
  never reaches the server (only public keys, credential IDs, sign counts).
- Registration: server challenge (32 random bytes, 5-minute TTL, one-time consumption),
  `residentKey: required` (passkeys are discoverable credentials), RP ID and allowed
  origins checked by the library against `SOLAROPS_WEBAUTHN_RP_ID` /
  `SOLAROPS_WEBAUTHN_ALLOWED_ORIGINS`, user verification required, credential-ID
  uniqueness enforced globally (cross-account registration returns 409).
- Authentication: challenge binding, credential ownership, RP ID, origin, signature,
  UV flags and sign-count regression checks (equal/non-advancing non-zero counts are
  rejected and audited). Discoverable logins omit `allowCredentials`; scoped logins
  include the account's active credentials.
- Revocation needs a fresh proof (step-up grant header or password). Revoked
  credentials return 401 `unknown_credential`; sessions are created only after
  successful server verification.
- Production guards: non-localhost RP ID and explicit HTTPS origins are required when
  `APP_ENV=production`. Localhost secure-context behavior was verified in the
  acceptance run (Chromium rejects IP-literal RP IDs, so the stack uses `localhost`;
  document the real origin/RP ID at deployment).

## MFA (TOTP + recovery codes)

- Secrets are Fernet-encrypted (key derived from the server secret); recovery codes are
  stored as HMAC hashes and consumed once.
- Enrollment is password-protected and completes only after a valid code; login with a
  verified factor stops at a short-lived ticket (HTTP 202) — no session exists until
  the ticket is redeemed. Failures run in a dedicated security transaction (same
  pattern as email-OTP verification) so attempt counts and lockouts persist despite
  the 401: 5 failures lock the factor for 15 minutes; ticket attempts are capped and
  tickets are single-use with expiry.
- Recovery-code login revokes all other sessions and never changes the account role
  (asserted in tests). Rate limiting applies per user/IP on top of lockouts.
- Email verification codes are never treated as second factors; passkey assertion is
  accepted as phishing-resistant strength for login (documented policy decision).

## Step-up for sensitive actions

- `POST /auth/step-up/start|verify-totp|verify-passkey` issues 10-minute grants
  consumed via the `X-Strong-Auth` header. Required for: extension-terms management,
  extension approval/rejection review, payment verification/activation, and factor or
  passkey revocation (password re-entry is accepted as the alternative reauthentication).
- Staff roles are untouched: public signup still creates customers only; admins still
  provision employees. Existing policies and warranty endpoints gained no new auth
  requirements (backward compatible); new sensitive endpoints carry the grant check.

## Findings fixed during implementation

1. Failed MFA attempts were rolled back with the request transaction, so lockouts
   never persisted. Fixed with dedicated security transactions (verified by the
   lockout test).
2. The frontend sent `allowCredentials: []` for discoverable logins, which forbids
   every credential. The key is now omitted unless non-empty.
3. The step-up ticket issuer did not know passkeys, so passkey-only users could not
   start step-up. `available_step_up_methods` now includes passkeys.
4. Registration did not request a resident key, so discoverable logins failed.
   `residentKey: REQUIRED` is now requested at registration.
