# Phase 4D SysCache

Customer intelligence snapshots for support operations, built from
real PostgreSQL records: profile, sites, orders, installations,
equipment serials, warranty coverage, open/historical tickets and
repair history. Passwords, sessions, OTPs, tokens and unrelated
personal data are never cached (covered by
`test_snapshot_content_and_no_secrets`).

## Key format

`{tenant}:{scope}:customer:{customer_user_id}` with tenant `default`
and scope `support-overview` (v1). Unknown scopes are rejected (400).

## Versioning and freshness

- `schema_version` (current `1`): readers rebuild on rollover.
- `business_version`: SHA-256 over the source rows (profile, sites,
  orders, serials, warranty, tickets, repair jobs). Any source change
  alters it, so staleness is detected without trusting the cache.
- `generated_at` / `expires_at`: TTL from `SOLAROPS_SYSCACHE_TTL_SECONDS`
  (default 900 s). `invalidated_at` marks event-driven staleness.

## Invalidation

- `phase4d_cache_outbox`: writers append in the same transaction as
  their business change (`POST /api/v1/cache/invalidate` is the
  Phase 4C integration contract: `aggregate_kind` `finance`/`payment`,
  idempotent on `event_id`).
- `drain_outbox` advances a per-consumer cursor (`phase4d_cache_consumers`).
  Invalidation is monotonic: a snapshot newer than the event is left
  alone, so late/out-of-order events only ever mark stale, never roll
  back (plus cursor realignment if the stream was reset).
- Concurrent rebuilds collapse on `pg_advisory_xact_lock(hashtext(key))`;
  the lock holder rechecks freshness before writing, so 8 concurrent
  refreshes leave exactly one row (tested).
- Cache outage or rebuild failure falls back to a live PostgreSQL
  build labeled `postgresql-fallback` (or serves the expired row as
  `cache-stale` with a reason). Forced via
  `SOLAROPS_SYSCACHE_FORCE_FALLBACK` for tests.

## Observability

`GET /api/v1/cache/metrics` exposes durable counters
(hits/misses/rebuilds/fallbacks); every response carries
`source`, `stale`, `stale_reason` and `build_ms`. No payload data is
logged.

## Isolation

Customers read only their own snapshot; support/admin read any;
technicians and other roles are denied (403). Tested, including
cross-customer denial.
