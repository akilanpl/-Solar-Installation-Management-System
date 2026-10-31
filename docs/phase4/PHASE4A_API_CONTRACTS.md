# Phase 4A API contracts

Prefix: `/api/v1`. Conventions follow `docs/api/API_CONTRACTS.md`: UUID ids,
ISO 8601 times, `{"error": {"code", "message", "details"}}` errors, CSRF
double-submit on unsafe methods, `Idempotency-Key` (8–80 chars,
`[A-Za-z0-9_-]`) on creates. Machine-readable source of truth:
`contracts/generated/openapi.json`; TypeScript: `apps/web/src/generated/schema.ts`.
Both were regenerated from the running app; the TypeScript was not hand-edited.

## Tickets

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| POST | `/tickets` | customer | 201, or 200 on idempotent replay. 404 for another customer's order or an unknown serial; 409 `serial_not_installed` for a non-installed unit; 409 `idempotency_conflict` on key reuse with a different body |
| GET | `/tickets` | customer (own), technician (assigned work), support, admin | `status` filter, `page`/`page_size`, `items`/`total` |
| GET | `/tickets/{id}` | owner, assigned technician, support, admin | Includes serial number, warranty row or null, repair jobs, acknowledgments |
| POST | `/tickets/{id}/triage` | support, admin | Body: category, verified_priority, note. `open` → `triaged` |
| POST | `/tickets/{id}/support-assignment` | support, admin | Body: support_user_id (active support/admin), optional note. Moves `triaged` → `assigned`, otherwise records history |
| POST | `/tickets/{id}/request-info` | support, admin | Body: message. Records the return state and moves to `waiting_customer` |
| POST | `/tickets/{id}/customer-reply` | owning customer | Body: message. Only from `waiting_customer`; returns to the recorded state |
| POST | `/tickets/{id}/notes` | support, admin | Internal note event, no status change |
| POST | `/tickets/{id}/escalation` | support, admin | Body: reason, optional verified_priority. Sets the escalated flag |
| POST | `/tickets/{id}/cancel` | owning customer (from `open`), support/admin (before work starts) | Reason required; cancels the open repair job too |
| POST | `/tickets/{id}/reopen` | owner, support, admin | From `resolved`, `customer_confirmed`, or `closed`. Reason required |
| GET | `/tickets/{id}/history` | same as ticket detail | Ordered transition and note events |
| GET | `/support/staff?role=technician\|support` | support, admin | Active staff with employee codes; technicians include live open-job counts |

## Repair jobs

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| POST | `/tickets/{id}/repair-jobs` | support, admin | From `triaged`/`assigned`. 409 `job_already_active` or `technician_unavailable` (cap of 5 open jobs, exact-slot clash). Idempotent |
| GET | `/repair-jobs` | technician (own only), support, admin | Optional `ticket_id` filter |
| GET | `/repair-jobs/{id}` | assigned technician, support, admin | |
| POST | `/repair-jobs/{id}/arrival` | assigned technician | Server clock; job `assigned` → `in_progress`, ticket `assigned` → `in_progress` |
| POST | `/repair-jobs/{id}/diagnostics` | assigned technician | Findings (≥10 chars), optional root cause and readings |
| POST | `/repair-jobs/{id}/work` | assigned technician | Work performed (≥10 chars), start/finish datetimes (finish must be later), parts as catalogue codes with positive quantities |
| POST | `/repair-jobs/{id}/submit` | assigned technician | Requires arrival, diagnostics, and work. 409 `arrival_required` / `diagnostics_required` / `work_required` otherwise |

## Attachments

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| POST | `/tickets/{id}/attachments` | owner, assigned technician, support, admin | Multipart `upload`; optional `?repair_job_id=` linkage. 413 over 5 MB, 422 on non JPEG/PNG/WebP/PDF |
| GET | `/tickets/{id}/attachments` | same as ticket detail | Metadata list |
| GET | `/tickets/{id}/attachments/{attachment_id}` | same as ticket detail | File bytes, `no-store` |

## Resolution and closure

| Method | Path | Roles | Notes |
| --- | --- | --- | --- |
| POST | `/tickets/{id}/resolution-ready` | support, admin | Only from `in_progress` with a submitted repair job. Bumps the version, snapshots the summary, moves to `resolved` |
| GET | `/tickets/{id}/resolution-summary` | same as ticket detail | Exact version, payload hash, and summary the customer must answer |
| POST | `/tickets/{id}/confirmation` | owning customer only | Body: `confirmed`/`disputed`, `summary_version`, note (required for disputes). 409 `stale_summary` / `duplicate_confirmation`; 403 for staff; confirm → `customer_confirmed`, dispute → `in_progress` |
| POST | `/tickets/{id}/close` | support, admin | Only from `customer_confirmed` with a matching confirmed acknowledgment |

## Error codes introduced

`serial_not_installed`, `job_already_active`, `technician_unavailable`,
`arrival_required`, `diagnostics_required`, `work_required`,
`confirmation_required`, `stale_summary`, `duplicate_confirmation`,
plus the shared `invalid_transition`, `idempotency_conflict`,
`idempotency_key_required`, `not_found`, `forbidden`, `file_too_large`.
