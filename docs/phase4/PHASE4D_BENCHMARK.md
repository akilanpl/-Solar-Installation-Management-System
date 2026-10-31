# Phase 4D Benchmark

Reproducible workload: `apps/api/tests/test_phase4d_benchmark.py`
(single installed order on disposable PostgreSQL, TestClient timing).
Nothing below is estimated; the test prints this table and writes
`/tmp/phase4d_benchmark.json` on every run.

## Measured results (2026-11-01, Apple Silicon, local PostgreSQL)

| Workload | n | p50 | p95 | mean |
|---|---|---|---|---|
| Cold GET (build + store) | 5 | 16.14 ms | 64.02 ms | 25.06 ms |
| Warm GET (cache) | 50 | 6.68 ms | 7.09 ms | 6.68 ms |
| PostgreSQL fallback (single) | 1 | 9.09 ms | — | — |

- Warm-phase hit rate: 1.0 (50/50 served from cache, identical business versions).
- Concurrent warm reads: 10/10 succeeded with one consistent version.
- Failure recovery: forced-fallback read succeeded; `fallbacks` counter ≥ 1.
- Server counters after run: hits 55, misses 5, rebuilds 5, fallbacks 1, 1 snapshot row.

## Reading the numbers

- The warm path still runs the indexed source queries needed to
  compute the business version, so it measures freshness-checked
  caching, not a blind key lookup. Cold adds payload assembly plus one
  row write under an advisory lock.
- p95 cold is dominated by first-compile/connection effects in a
  sample of 5; warm p50/p95 are tight (6.68/7.09 ms).
- No claim is made about production hardware, larger datasets, Redis
  comparisons or multi-customer contention beyond the 10-thread check.
