# Phase 4D Parallel Integration Handoff

## Provenance

- Phase 4B base SHA: `26a5f129e1eeea5ad772ab4e1b8c5f8d43bc3d`.
- Final Phase 4D commit: tip of branch `feature/phase4d-intelligence`
  (local only, not pushed, not merged). Verify with
  `git log --oneline -8` on the worktree; the exact SHA is stated in
  the handoff message.
- Added migration: `4d1a2b3c4d50` on top of `4b1c2d3e4f51`.
  Single head verified (`alembic heads` → `4d1a2b3c4d50`).

## Isolation statement

SOL's worktree/branch/databases and the 4A/4B worktrees were never
touched; SOL's unfinished 4C commits were never merged. Only
`solarops_4d_preview` and `solarops_release_test_20261101` were
created/used; only ports 8014/3014. No hooks bypassed; no quality
gate weakened (one migration-pin test updated per convention, with
new-table coverage added).

## Changed shared surfaces (reconciliation watch-list)

- `app/models/__init__.py`: import block only (phase4d added in order).
- `app/api/v1/router.py`: one `include_router` line.
- `app/core/config.py`: new optional settings (defaults = current
  behavior; no existing test affected).
- `app/components/shell.tsx`: three nav links.
- `contracts/generated/openapi.json`, `apps/web/src/generated/schema.ts`:
  regenerated (13 new paths; billing `EstimateResponse` untouched after
  the 4D rename to `GenerationEstimateResponse`).
- `apps/api/tests/test_phase3_migrations.py`: head pin + 7 FK-backed
  table names.

## Phase 4C extension contract (ready, handler deferred)

Finance/payment writers call `emit_invalidation` (same transaction) or
`POST /api/v1/cache/invalidate` with `aggregate_kind` `finance` or
`payment`, `aggregate_id`, `customer_user_id`, `event_id`
(idempotent). The SysCache consumer picks it up without any 4D-side
change. The actual 4C handler wiring happens at combined integration.

## Integration steps after SOL finishes

1. Verify final 4C/main SHA. 2. Reconcile 4C against accepted 4B
   baseline. 3. Reconcile 4D against that result; if 4C created a
   parallel Alembic head, merge heads (never rewrite either branch).
4. Regenerate contracts; re-run full backend + frontend + browser
   acceptance on the merged tree. 5. Wire 4C finance events to the
   invalidation endpoint. 6. Configure providers (AI model, weather,
   device) or keep the honest unavailable paths.

## Known limitations

- No providers configured: AI is deterministic-labeled, weather is
  unavailable-by-design, actual generation has no device source.
- Interactive browser operation not exercised here (no runner);
  covered by unit/typecheck/build/HTTP serving evidence.
- Benchmark numbers are local-workstation measurements, not
  production capacity claims.
