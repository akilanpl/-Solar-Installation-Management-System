# Workflow states

## Account

1. `POST /api/v1/auth/signup` creates an unverified customer and a challenge.
2. `POST /api/v1/auth/verify-email` sets `email_verified_at` when the HMAC matches, the challenge is unconsumed, and it has not expired.
3. Login before verification returns `email_not_verified` and does not set a session cookie.
4. Logout sets `sessions.revoked_at`. Later calls with that cookie return `unauthenticated`.

Wrong, expired, and reused codes all return `invalid_verification_code`. Expired and wrong codes consume or increment the challenge inside the database. A reused code no longer matches an active challenge.

Company-provisioned employees are created with `email_verified_at` set, because the administrator is asserting an out-of-band identity check. That is not how public signup works.

## Enquiry

`QUALIFICATION_TRANSITIONS` in `app/models/enquiry.py`:

| From | Allowed next |
| --- | --- |
| `submitted` | `under_review`, `qualified`, `not_qualified` |
| `under_review` | `qualified`, `not_qualified` |
| `qualified` | `under_review` |
| `not_qualified` | `under_review` |

The customer create always starts at `submitted` and writes a history row with a null previous status. Sales or admin move the status. Repeating the current status is rejected with `invalid_transition`. `not_qualified` requires a note of at least 3 characters.

The same transaction writes `enquiries.status`, `enquiry_status_history`, and `audit_events`.

Idempotency: the same customer, key, and body returns the original enquiry with HTTP 200. The same key and a different body returns `idempotency_conflict` and does not insert.

## Not in Phase 1

Survey approval, quotation acceptance, payment, picking, delivery, warranty, and ticket closure have no state machine in code yet. Their intended order is documented with the planned endpoints. Do not mark an enquiry `qualified` as if a quote had been accepted. Qualification only means sales has reviewed the request.
