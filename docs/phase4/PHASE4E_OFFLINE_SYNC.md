# Phase 4E — Offline Sync

## Allowed offline actions (closed set)

`survey_draft`, `measurement`, `repair_diagnostics`, `repair_work`, `repair_checklist`,
`evidence_intent`. Anything else — settlements, ledger postings, warranty decisions,
signature acceptance, OTP, invoicing, payroll, closures — has no operation type and is
rejected with `forbidden_offline_action`. Offline work never changes a record's status:
draft fields only, never submit/approve/close.

## Protocol

Each queued operation carries `client_operation_id` (idempotency key) and
`base_field_version` (the record version seen offline):

1. Revalidate authentication (401 → client marks `auth_required`, nothing is faked).
2. Recheck authorization (technician owns the survey/job; others 404).
3. Validate business state (non-editable states reject; terminal states reject).
4. Compare versions: mismatch → `conflict` (no silent overwrite; client rebases).
5. Apply idempotently: a repeated key returns the stored verdict (`duplicate: true`).
6. Evidence uploads reuse the same key: identical bytes return the stored record;
   differing bytes with the same key return 409.

Verdicts per operation: `applied`, `conflict`, `rejected` (+ transport-level `failed`
/ `auth_required` client-side). Batches of up to 25 run each operation in its own
savepoint, so one bad entry never poisons the rest.

## Versioning

`field_version` (default 0) was added to `surveys` and `ticket_repair_jobs`. Online
writes bump it too (`record_diagnostics` / `record_work`), so an offline base version
detects online edits, not just other offline writes. Survey submissions change status,
which the state gate already rejects — no silent overwrite is possible either way.

## Client storage

- IndexedDB (`solarops-offline`, schema version 1), per-user isolation, only the
  whitelisted draft fields plus queue metadata — no customer PII beyond what the
  assignment screen already shows.
- Cached assignments carry `cached_until` (7-day retention); the client purges expired
  snapshots and wipes a user's queue on logout/account switch (server also scopes all
  reads by session user).
- States shown: draft, queued, syncing, synced, conflict, failed, sign-in required.
  `auth_required` never claims success.
- Evidence: file input → `POST /offline/evidence` (JPEG/PNG/WebP/PDF, 5 MB);
  retries are idempotent; offline capture keeps the file until connectivity returns.
- No service worker: the shell is server-rendered per role and caching it would risk
  stale authorized content. IndexedDB + `online`/`offline` events fully cover the
  workflow; this is documented, not deferred.

## What the tests prove

- Draft applies once; replay returns the stored verdict without touching the row.
- Stale versions conflict after both offline and online edits (rebases then apply).
- Submitted surveys and finished jobs reject offline writes.
- Cross-technician writes and cross-user queue reads fail closed.
- Evidence retry returns the same record; tampered bytes conflict.
- Forbidden operation types are rejected with a named error.
