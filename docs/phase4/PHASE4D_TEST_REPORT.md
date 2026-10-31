# Phase 4D Test Report

Base SHA `26a5f12` (203 backend tests passing, ruff clean) → HEAD
`b35b2b9` + checkpoints below. Disposable database
`solarops_release_test_20261101` (matches the repo's disposable-DB gate).

## Backend: 237 passed, 0 failed

- Inherited 203 (full Phase 1–4B regression, including the migration
  head-pin test updated to `4d1a2b3c4d50` per convention).
- 34 new Phase 4D tests:
  - `test_phase4d_syscache.py` (11): content/secrets, warm hits,
    owner isolation, scope rejection, invalidation flow, idempotent
    emit, out-of-order skip, 8-thread single-row rebuild, forced
    fallback, schema rollover, technician denial.
  - `test_phase4d_assist_weather_generation.py` (20+unit): assist
    extraction/labeling, missing info, confirm single-use, customer
    confirm denial, no ticket mutation, unsafe-output rejection,
    injection neutralization, provider unavailable/timeout/success,
    weather unavailable/unverified/bad-coords, storm advisories,
    affected visits + ack flow, estimate shape/ordering/errors,
    reading dedup/quarantine/rejection, ingest denial, honest empty state.
  - `test_phase4d_benchmark.py` (1): measured cold/warm/fallback,
    hit rate, concurrency, recovery (see PHASE4D_BENCHMARK.md).
  - `test_phase4d_contract.py` (2): single head, 13 intelligence
    paths in OpenAPI.

## Frontend

- `npm test`: 15 passed (12 inherited + 3 new intelligence label tests).
- `npm run typecheck`, `npm run lint`: clean.
- `npm run build`: succeeds; routes `/support/intelligence`,
  `/support/weather`, `/customer/generation` emitted.
- `npm audit`: 16 moderate, 0 high/critical (baseline profile).

## Live preview acceptance (API 8014, web 3014, DB solarops_4d_preview)

- `GET /api/v1/health` → 200; intelligence paths → 401 unauthenticated.
- Support login → 200; snapshot cold `cache-rebuilt` → warm `cache`
  with all 8 sections; metrics live; deterministic AI draft returned;
  weather availability `false` with honest banner path.
- Web preview serves `/login` (200) and the three new pages compile.

## Not verified

- Interactive browser operation (no browser runner in this environment;
  not installed, per policy). DOM behavior is covered by unit tests,
  typecheck, build and HTTP-level page serving only.
- Production hardware performance; provider-backed AI/weather/device
  paths (no providers configured — covered by stub/timeout tests).
