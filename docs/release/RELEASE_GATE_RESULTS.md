# Mandatory release gate

Application/test candidate `88766362fb7842b2da12be73d254d81cd627c9c8` on `fix/actual-frontend-integration`. Verification 2026-10-31. Main is not merged; Phase 4 has not started.

**INCOMPLETE — 57.8/100, grade F.** Score is produced unchanged by `.pushgate/score.py`; no threshold was lowered, test skipped, notrun family removed or override used.

| Mandatory gate | Status |
|---|---|
| Branch reconciliation through 72db4a1 / QA ebf107b | Reviewed/adapted; see FINAL_BRANCH_RECONCILIATION.md |
| Backend full PostgreSQL/unit regression | PASS: 269 |
| Empty migrations/single head/ORM parity/preserved records | PASS executed checks, head f3b9c0d1e2a3 |
| Frontend frozen install/tests/types/lint/generation/build | PASS executed checks, 27 tests |
| Backend line / branch coverage | 90.794% PASS / 70.39% PASS |
| Diff coverage | Backend 92.746%; full frontend/backend diff campaign incomplete |
| Test mutation integrity | Seven fault probes detected; exhaustive changed-code mutation campaign NOT RUN |
| Primary browser customer-to-warranty | PARTIAL through accepted quote; provider step BLOCKED |
| Provider sandbox/webhook | BLOCKED: configuration absent; mocks do not count |
| Load | PASS scoped 300s read-only workload; wider stress/soak/resilience campaign incomplete |
| Browser accessibility/compatibility | Manual keyboard/viewport checks partial; axe/Firefox/WebKit NOT RUN |
| Outgoing secrets | PASS scan; unrelated-history exposure review remains |
| Dependencies | Zero high/critical frontend advisories; zero known backend advisories; moderate frontend findings retained |
| Backup / restore / readiness / request traces | PASS executed local checks; not production deployment evidence |
| Main baseline ratchet / two-order remote CI | NOT RUN for this candidate |
| Phase 3 complete operations | Important custody/scheduling/coverage flows tested; dedicated replacement/carrier-return lifecycle remains open |
| Exact-head remote CI | NOT RUN: candidate is local; old draft CI is historical only |
| Main merge / fresh-main checkout / Phase 4 entry | BLOCKED |

Runner stages:

- `stage-gate-selftest`: PASS
- `stage-lint-api`: PASS
- `stage-backend`: PASS
- `stage-backend-coverage-export`: PASS
- `stage-backend-coverage-check`: PASS
- `stage-frontend`: PASS
- `stage-typecheck`: PASS
- `stage-lint-web`: PASS
- `stage-build`: PASS
- `stage-dependency-audit`: PASS

The original six missing campaign categories and ten P0 notrun family markers remain enforced. Individual local evidence above does not silently satisfy those complete campaign gates. No new push, PR merge, main merge or Phase 4 implementation was attempted with an incomplete gate.

Reproduce from repository root (only the explicitly disposable DB is destructive):

```sh
SOLAROPS_TEST_DATABASE_URL=postgresql+psycopg:///solarops_release_test_20261031 SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=solarops_release_test_20261031 SOLAROPS_NEXT_DIST_DIR=.next-ultimate NEXT_PUBLIC_SOLAROPS_ENV=development NEXT_TELEMETRY_DISABLED=1 python3 .pushgate/run.py
```

Stop only the owned Next server using `.next-ultimate` before this build stage. Preserve the candidate DB, ignored private configuration, uploads and backups.
