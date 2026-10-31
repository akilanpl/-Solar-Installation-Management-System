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

Qualifying an enquiry also stores the shadow-free roof area in square metres, whether the grid connection is suitable, the deciding employee, and the decision time. A survey can be opened only while the enquiry is `qualified`.

If an approved survey already exists, changing the shadow-free area or the grid-suitability flag returns `qualification_locked` unless the request sets `acknowledge_downstream`. That acknowledgement updates the enquiry and the audit row only. It does not edit the survey, the quotation lines, or the order.

## Survey

`draft` → `assigned` → `in_progress` → `submitted` → `approved` or `rejected`.

| Action | Who | Rule |
| --- | --- | --- |
| Open | sales, admin | Enquiry is `qualified`, and no survey for it is still open or approved. |
| Assign | sales, admin | From `draft` or `assigned`. Appointment stays `pending` unless the request includes a real timestamp. |
| Start and submit | assigned technician | Submit requires azimuth, tilt, shadow-free area, and cable distance. |
| Approve or reject | sales, admin | From `submitted` only. Rejection needs a note. |
| Resurvey | sales, admin | Only from `rejected`. The old row stays `rejected`. The new row points at it. |

A rejected survey cannot be quoted. Approval writes the decision and the audit event in the same transaction.

## Quotation

A quotation is inserted as `issued`. There is no editable draft. Lines, template version, tax, and totals are written once.

| From | To | Who |
| --- | --- | --- |
| `issued` | `superseded` | sales, by issuing a new revision |
| `issued` | `withdrawn` | sales |
| `issued` | `accepted` | the owning customer |

Acceptance rejects a superseded, withdrawn, or expired revision, a quotation for another customer, and a quotation whose survey is not approved. The acceptance row is unique per quotation. Two concurrent accepts lock the quotation; one commits and the other gets `already_accepted`.

## Payment

`pending` → `processing` → `verified`, `failed`, or `unresolved`.

A sandbox intent is `is_test_only`. Calling the sandbox outcome endpoint is the development adapter, and production refuses it. `unknown` stays `unresolved`. A cash receipt is `verified` only when sales or admin records it. Uploading a reference does not verify anything. The same idempotency key does not create a second intent.

## Order

Sales confirms an order only from the accepted quotation after verified payments cover the stored advance. The order, frozen lines, warehouse preparation request, and installation scheduling request are inserted in that request's transaction. The scheduling slot is null. Stock is not changed. The same quotation cannot get a second order. Repeating the same idempotency key returns the original order.

## Still later

Picking, serials, dispatch, delivery, warranty, and ticket closure are not states in this phase. A confirmed order is not installed equipment.
