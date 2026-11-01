# Phase 4B Parallel Integration Handoff

## Provenance

- Phase 4A base SHA: `adc2166` (local checkpoint, migration `f4a7b2c1d093`).
- Phase 4B HEAD SHA: `5bf3680` on `feature/phase4b-warranty-repair` (local only,
  never pushed, never merged to `main`).
- Added revisions: `4b1c2d3e4f50` (domain), `4b1c2d3e4f51` (index alignment).
- Checkpoints: `d433d7c` warranty engine, `d3fbd9a` replacement, `14440e1`
  billing, `0801708` workspaces, `5bf3680` acceptance + alignment.

## Isolation statement

SOL and Phase 4A worktrees, branches, databases (`solarops`, `solarops_test`,
`solarops_dev`, release DBs), and ports were never touched. Only
`solarops_4b_preview` and `solarops_release_test_20261102` were created/used.
Shared auth/inventory code was reused read-only except one additive guard
widening (warehouse roles may read replacement rows, committed in checkpoint 4).

## Changed shared surfaces (reconciliation watch-list)

- `app/models/phase3.py`: serial statuses +`returned`, `quarantined`.
- `app/services/replacement_service.py`: warehouse read scope.
- `contracts/generated/openapi.json`, `apps/web/src/generated/schema.ts`:
  regenerated (17+ new paths).
- `apps/web/src/components/shell.tsx`: nav links only.
- `apps/api/tests/test_phase3_migrations.py`: head pin + 4B table list.
- New migration ancestry on top of `f4a7b2c1d093` may conflict with SOL
  integration migrations; reconcile ancestry before merge.

## Reconciliation order (after SOL final `main`)

1. Verify final main SHA. 2. Reconcile 4A against final main. 3. Validate
   combined migrations + contracts. 4. Run combined Phase 1–3 + 4A tests.
2. Review 4A. 6. Reconcile 4B against accepted 4A baseline. 7. Resolve shared
   migrations/services. 8. Run all tests + browser acceptance. 9. Publish 4B
   separately.

## Readiness verdict

Integration-ready checkpoint, NOT production-ready: isolated branch, no
payment/manufacturer providers, push intentionally held for review.
Do not start Phase 4C on this branch.
