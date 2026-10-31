# Security model

The browser is not trusted for identity, role, or ownership.

## Passwords and codes

`hash_password` in `app/core/security.py` uses Argon2id with time cost 2, 19 MiB of memory, and parallelism 1. Session cookies and OTP codes are stored as HMAC-SHA256 digests keyed by `SOLAROPS_SECRET_KEY`. The raw OTP is not a database column. In development it is written only to the mailbox file, which is the captured email.

Login of an unknown user still runs `dummy_password_check` so the response time is closer to a real Argon2 verification.

## Sessions

`authenticate` creates a new session row and sets `solarops_session` as `HttpOnly`, `SameSite=Lax`, and `Secure` when `SOLAROPS_COOKIE_SECURE=true`. Logout sets `revoked_at`. `user_from_session_token` rejects a missing, revoked, or expired session. The token in the cookie is not the primary key; the database stores the HMAC.

Session lifetime is `SOLAROPS_SESSION_TTL_HOURS` (12 by default). It does not slide.

## CSRF and origin

Unsafe methods need the double-submit cookie. `GET /api/v1/auth/csrf` sets `solarops_csrf` so JavaScript can echo it in `X-CSRF-Token`. Login rotates that cookie. `require_csrf` compares the header and cookie with `hmac.compare_digest` and rejects an `Origin` that is not in the trusted list.

The supported browser path is the Next.js proxy, so the page and the API are the same site.

## Roles

`users.role_code` is a foreign key to `roles`. Public signup in `auth_service.signup` always writes `customer`. `provision_employee` requires the actor's role to be `admin` and refuses the customer role.

`LoginRequest.intended_role` is discarded in `app/api/v1/auth.py` (`_ignored_client_role_hint`). The login screen's dropdown only chooses email lookup versus employee-id lookup (`account_kind`). A customer who sends `intended_role: "admin"` still receives `role: "customer"`, and `GET /api/v1/admin/employees` returns 403.

Customers read enquiries through `get_visible_enquiry`. Another customer's id returns 404, not the row. Sales and admin can list every enquiry. Other roles receive 403. Qualification uses the same role check inside `qualify_enquiry`, not a hidden button.

## Rate limits

`RateLimiter` is in memory for this process. Login, signup, OTP verification, and resend each have a window. Restarting the API clears the counters. Do not treat this as a shared edge limiter. OTP attempts are also stored on the challenge row and survive a restart; five failures consume the challenge (`SOLAROPS_OTP_MAX_ATTEMPTS`).

## Failures

Known errors use `{"error": {"code", "message", "details"}}`. `create_app` maps unexpected exceptions to `internal_error` without the traceback. Integrity errors become `conflict`. A database outage on `/api/v1/ready` becomes `database_unavailable`. `/api/v1/health` does not touch the database.

## Production gaps

- SMTP is implemented with `smtplib` only when `SOLAROPS_SMTP_HOST` is set. There is no pretend success. Without it, production startup of the email sender raises `email_not_configured`.
- The example secret is rejected when `SOLAROPS_APP_ENV=production`.
- Cookies must be `Secure` behind HTTPS. Set `SOLAROPS_COOKIE_SECURE=true`.
- The rate limiter is per process.
- Passkeys are not implemented. The planned contract is in the API document.
