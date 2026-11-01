# Phase 4D Architecture

Provisional checkpoint on top of Phase 4B. No Phase 4C code is merged,
touched or awaited.

## Provenance

- Phase 4B base SHA: `26a5f129e1eeea5ad772ab4e1b8c5f8d43bc3d` (`26a5f12`).
- Branch: `feature/phase4d-intelligence` (local, never pushed, never merged).
- Worktree: `~/Downloads/SOLOPS-phase4d` (SOL's 4C worktree/branch untouched).
- Databases (disposable, owned by this workstream only):
  `solarops_4d_preview`, `solarops_release_test_20261101`.
- Ports: API `8014`, web `3014` (confirmed free before use).

## Modules added

| Area | Backend | Frontend |
|---|---|---|
| SysCache | `models/phase4d.py` (9 tables), `services/syscache_service.py`, `api/v1/intelligence.py` | `components/intelligence.tsx`, `app/support/intelligence/page.tsx` |
| AI assist | `services/ai_assist_service.py` | same support page |
| Weather | `services/weather_service.py` | `components/weather.tsx`, `app/support/weather/page.tsx` |
| Generation | `services/generation_service.py` | `components/generation.tsx`, `app/customer/generation/page.tsx` |
| Contracts | `schemas/phase4d.py`, migration `4d1a2b3c4d50` | regenerated `contracts/generated/openapi.json`, `src/generated/schema.ts` |

Shared files changed additively only: `models/__init__.py` (import order),
`api/v1/router.py` (one include), `core/config.py` (new optional settings),
`components/shell.tsx` (nav links), `tests/test_phase3_migrations.py`
(head pin + table list, per convention). The billing `EstimateResponse`
contract is preserved: the Phase 4D schema is named
`GenerationEstimateResponse` to avoid a collision.

## Design principles

- PostgreSQL is authoritative everywhere. The cache is a documented
  database-backed snapshot table, never a second source of truth.
- External providers are boundaries with capability checks: unavailable
  means an explicit BLOCKED/unavailable state, never simulation.
- Machine output never mutates business records without a recorded
  human confirmation.
- Estimates are labeled with model, assumptions and units; verified
  readings require authenticated ingestion and deduplication keys.
