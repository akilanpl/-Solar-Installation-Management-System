# Phase 4A architecture — complaint to customer-confirmed resolution

Branch: `feature/phase4a-support`. Base: integration release `ebf107b`
(Phases 1–3, migration head `e6a2b3c4d5f6`). Phase 4A migration:
`f4a7b2c1d093`.

## Gate position

The Phase 4 entry gate (`docs/release/PHASE4_ENGINEERING_GATE.md`) requires
gates A–F or a separately approved scope that names the remaining blockers.
This mission is that scope for the support-ticket and customer-confirmed
resolution capabilities only. Everything else in the gate contract
(warranty-aware repair billing, SysCache, weather, generation, scheduling
integration, accounting, subsidies) stays NOT IMPLEMENTED.

The integration verdict records known gaps that bound this phase: no
serial-level policy warranty, no skill/hour/overlap-aware scheduling, and no
browser acceptance. Phase 4A is designed inside those bounds: warranty rows
are shown read-only, technician eligibility is active-role plus a real open-job
cap and exact-slot clash check (no invented skills, travel, or slots), and no
notification provider is claimed.

## Data design (additive, PostgreSQL is the source of truth)

New tables in `apps/api/app/models/support.py`, created by additive migration
`f4a7b2c1d093_phase4a_support_tickets.py`. No existing table was altered.

| Table | Purpose | Key constraints |
| --- | --- | --- |
| `service_tickets` | Complaint: owner, order, optional installed serial, symptoms, customer urgency, support classification, status, resolution version + snapshot | `UNIQUE (customer_user_id, idempotency_key)`, `UNIQUE (reference)`, FKs to customer profile, site, order, serial; status/urgency/priority/category check constraints |
| `service_ticket_events` | Append-only transition history: actor, timestamp, from/to, reason, evidence | Indexed `ticket_id`; never updated or deleted by any route |
| `service_ticket_attachments` | Evidence custody: storage key, filename, type, size, uploader, optional repair-job link | `UNIQUE (storage_key)`, 1 byte–5 MB check; file bytes live under the configured evidence directory |
| `ticket_repair_jobs` | Technician repair assignment linked to the originating ticket, order, and serial | `UNIQUE (ticket_id, idempotency_key)`, `UNIQUE (reference)`, status check; one open job per ticket enforced by the service under a row lock |
| `resolution_acknowledgments` | Immutable customer verdict bound to one exact resolution version and payload hash | `UNIQUE (ticket_id, summary_version)`, decision check; insert-only, no update or delete route |

Deliberately absent: no duplicate of the Phase 3 `installation_jobs` model
(repair work has different gates and a different lifecycle), no separate
`support_assignments` table (the current owner is a column; every change is a
history event), no price/billing columns on parts (Phase 4B owns billing;
parts are recorded as catalogue codes plus quantities only).

## State machine

`TICKET_TRANSITIONS` in `app/models/support.py`:

- `open` → `triaged`, `cancelled`
- `triaged` → `assigned`, `waiting_customer`, `cancelled`
- `assigned` → `in_progress`, `waiting_customer`, `cancelled`
- `in_progress` → `waiting_customer`, `resolved`
- `waiting_customer` → `triaged`, `assigned`, `in_progress` (customer reply
  returns to the recorded pre-request state)
- `resolved` → `customer_confirmed` (confirm), `in_progress` (dispute/reopen)
- `customer_confirmed` → `closed`, `in_progress` (reopen)
- `closed` → `in_progress` (reopen with reason)
- `cancelled` → terminal

Escalation is a recorded event plus an `escalated` flag and optional priority
change, not a state. Every transition locks the ticket row
(`SELECT ... FOR UPDATE`), validates against the table, and writes the event
row plus an `audit_events` row in the same transaction. The customer urgency
is stored separately from the support-verified priority and never treated as
a severity classification. No repair deadline is promised anywhere: the UI
states that assignment depends on real availability.

## Repair jobs and eligibility

A repair job references the ticket, order, and serial. Only users with an
active `technician` role can be assigned. Availability is real: at most five
open repair jobs per technician and no two open jobs at the same planned
time, both checked inside the assignment transaction. The technician path is
arrival (server clock) → diagnostics → actual work with recorded start/finish
and catalogue-validated parts → evidence upload → summary submit. Submit is
refused without arrival, diagnostics, and work, so a completed repair can
never be fabricated. Technicians list and read only their own jobs; anything
else answers 404.

## Customer-confirmed resolution

Support marks a submitted repair ready, which snapshots the summary, bumps
`resolution_version`, and moves the ticket to `resolved`. The owning customer
reads the exact summary and posts `confirmed` or `disputed` with the version
they saw. The backend rejects stale versions, duplicate answers for a
version, cross-customer posts (404), and support self-confirmation (403; the
route requires the customer role and ownership). A dispute returns the ticket
to `in_progress` with the reason preserved and forces a new resolution
version. Closure requires the `customer_confirmed` state plus a matching
confirmed acknowledgment. A failed confirmation rolls back with no
acknowledgment row and no status change.

## Security and reliability

- Ownership is resolved from the session on every call; bodies forbid extra
  fields and cannot set owner, status, or reference.
- Wrong-owner reads answer 404; wrong-role calls answer 403.
- Attachments are magic-byte sniffed (JPEG/PNG/WebP/PDF), capped at 5 MB,
  stored under generated keys, and downloads re-check ticket visibility with
  `no-store` headers. An orphaned file is deleted if the database write fails.
- Creates require `Idempotency-Key`; replays return the original row, reused
  keys with different bodies return 409.
- No external notification is sent or claimed; warranty billing is explicitly
  deferred to Phase 4B in code, UI copy, and docs.
