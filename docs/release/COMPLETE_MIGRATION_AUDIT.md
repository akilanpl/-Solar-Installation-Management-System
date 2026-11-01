# Complete migration audit

## Graph and reconciliation

Final intended head: `6a1b2c3d4e50`, a merge of:

- `f3b9c0d1e2a3`: accepted frontend/backend integration hardening lineage.
- `4c1c2d3e4f50`: finance subledger.
- `4d1a2b3c4d50`: intelligence.
- `35958a00676d`: strong authentication, offline work, warranty extensions.

The first lineage branches at `e6a2b3c4d5f6`; the three Phase 4 heads descend from
`f4a7b2c1d093` → `4b1c2d3e4f50` → `4b1c2d3e4f51`.
Revision identifiers and ancestry are retained. The merge drops/recreates only the
serial status CHECK with the union of all legitimate custody states. It changes
no source rows and retains unknown-status rejection.

## Necessary non-destructive compatibility corrections

A terminal merge cannot repair a CHECK that fails *before reaching the merge*.
Older `4b1c2d3e4f50`, `c0e6f7a8b9d0`, and `f3b9c0d1e2a3` upgrade definitions each
replaced the equipment status CHECK with their own branch's incomplete state set.
Combining them rejected existing `registered`, `delivered`, `missing`, `returned`
or `quarantined` rows depending on the starting branch. Only these upgrade CHECK
expressions are widened to the complete union; their IDs, parents, other DDL and
existing downgrade behavior remain. The new merge applies the correction to
already-migrated databases as well. No existing serial state is translated,
deleted, backfilled into an invented custody state, or temporarily removed.

Phase 4B also inserted `QUARANTINE`, already seeded by the integration lineage.
Its seed now uses `ON CONFLICT (code) DO NOTHING`, preserving existing location
records and names. This resolved an observed preserved-data upgrade failure.

## Executed checks

Dedicated disposable database: `solarops_release_test_20261103` on existing local
PostgreSQL, owned by the development role. No preview/production databases reset.

`tests/test_phase3_migrations.py`: **5 passed**. This includes:

- Fresh schema migration and SQLAlchemy metadata comparison.
- Phase 1 enquiry preservation across the documented disposable roundtrip.
- Saved quotation, acceptance, payment, order, stock and audit row hash checks
  across the earlier hardening roundtrip.
- Real `f3b9c0d1e2a3` schema with saved registered/delivered/missing serials upgraded
  to the single final head, preserving all selected existing row values.
- Real `4b1c2d3e4f51` schema with returned/quarantined serials upgraded identically.

Both sibling cases also exercise every valid final status and verify an invented
status still raises a PostgreSQL integrity error. The legacy survey snapshot
compares columns that existed before 4E and explicitly requires its new
`field_version` to be zero before the disposable downgrade; a dropped additive
column is not misreported as corruption of legacy data.

Ruff on the changed migration test/new merge revision and `git diff --check` pass.
The inherited Starlette/httpx deprecation warning remains.

## Recovery limits and remaining release checks

Downgrades can remove phase-owned records. They are not an authorized production
rollback. Use a verified backup and isolated restore rehearsal before deployment;
never run the disposable schema-reset test against business/preview databases.
The merge downgrade deliberately preserves the union CHECK because narrowing it
could invalidate legitimate records. Individual existing downgrade guards remain.

These migration tests do not alone certify the full release. Final consolidated
SHA still requires the complete backend/browser/gate campaign, backup/restore
rehearsal, and appropriate review. No final-source release acceptance is claimed.
