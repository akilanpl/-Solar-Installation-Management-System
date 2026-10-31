# Phase 4D Test Report

Base SHA `26a5f12` (203 backend tests passing, ruff clean). Disposable
database `solarops_release_test_20261101` (matches the repo's
disposable-DB gate); browser-QA database `solarops_4d_preview`.

## Backend: 253 passed, 0 failed

- Inherited 203 (full Phase 1–4B regression, including the migration
  head-pin test updated to `4d1a2b3c4d50` per convention).
- 50 new Phase 4D tests:
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
  - `test_phase4d_edge_cases.py` (16): unknown-ticket/site/order 404s,
    cross-customer/technician denials, customer refresh/metrics denial,
    invalid kinds/actions/statuses (400/422), duplicate forecast
    request keys, bad-payload/timeout provider failures, unknown
    capacity 422, blank reading fields, discard + expiry + oversize
    confirmation guards, malformed/unsafe provider drafts.
  - `test_phase4d_benchmark.py` (1): measured cold/warm/fallback,
    hit rate, concurrency, recovery (see PHASE4D_BENCHMARK.md).
  - `test_phase4d_contract.py` (2): single head, 13 intelligence
    paths in OpenAPI.

## Frontend

- `npm test`: 15 passed (12 inherited + 3 new intelligence label tests).
- `npm run typecheck`, `npm run lint` (incl. new spec/config): clean.
- `npm run build`: succeeds; routes `/support/intelligence`,
  `/support/weather`, `/customer/generation` emitted.
- `npm audit`: 16 moderate, 0 high/critical (baseline profile).

## Release gate (`.pushgate/run.sh`, disposable test DB)

- Stages: gate-selftest, lint-api, backend, coverage-export,
  frontend, typecheck, lint-web, build — all pass. Verdict INCOMPLETE
  55.6/100 on structural missing campaigns (same categories as the
  Phase 4 baseline: browser journey, load/resilience, mutation,
  secret-scan, ratchet, Phase 3 scope).
- `backend-coverage-check`: line 89.2% (threshold 80, pass); branch
  65.4% (threshold 70, fail). Pre-existing, not a 4D regression:
  excluding the 266 new 4D branches (65.0% covered) leaves the rest at
  63.9% — the baseline tree fails the same threshold.
- `dependency-audit` stage: registry endpoint errored (network), so
  the stage records fail; the manual `npm audit` evidence above
  (16 moderate / 0 high) stands.

## Browser acceptance (Playwright chromium, `playwright.4d.config.ts`)

3/3 passed in 24.6 s against API 8014 + web 3014 + clean
`solarops_4d_preview` (config-owned servers, real Chromium, no mocks):

- Support intelligence: UI login, unknown-snapshot 404 surfaced,
  supervised draft generated with deterministic label, discarded.
- Weather operations: unavailable banner shown, no synthetic data.
- Customer generation: UI signup → verify → login, empty state shown.
- Zero page errors in all three journeys.

## Live preview smoke (earlier session, servers since stopped)

- `GET /api/v1/health` → 200; intelligence paths → 401 unauthenticated.
- Support login → 200; snapshot cold `cache-rebuilt` → warm `cache`
  with all 8 sections; metrics live; deterministic AI draft returned;
  weather availability `false`.
- Full UI path verified through the web proxy (3014 → 8014 → DB):
  proxy login 200, proxy snapshot served, new pages compile (243 ms)
  and serve 200.

## Not verified

- Production hardware performance; provider-backed AI/weather/device
  paths (no providers configured — covered by stub/timeout tests).
