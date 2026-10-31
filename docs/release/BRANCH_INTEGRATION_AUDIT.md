# Branch integration audit

Status: PARTIAL. Remote refs fetched on 2026-10-31. The inventory is exhaustive for fetched origin branches; source/security review is targeted, not a claim that every line has been audited.

The original four-page problem statement and `~/Downloads/SolarOps_Final_Build_Spec.md` were found and read. The exact `(1)` filename was absent. The current final-build document distinguishes official stories from team enhancements.

## Current branches and ancestry

| Branch | HEAD | Merge base with remote main | Authors preserved |
|---|---|---|---|
| origin/feature/backend-workflows | b979ec6fa01974265faf0275f520b8fa41d33017 | b979ec6fa01974265faf0275f520b8fa41d33017 | Akilan |
| origin/feature/frontend-workplaces | 74f4734cc73212e235e7f256c2bd327634b3b5dd | No common ancestor | ashwin-hue |
| origin/feature/frontend-workspaces | 81addc8539d69e5d39df3db545567c833350a87a | 81addc8539d69e5d39df3db545567c833350a87a | Akilan |
| origin/feature/phase3-warehouse-installation | ae212b2cdfce755b69ec9a73df15f3907873bf0d | a95533838fd4413233ed69edf2ce671260ea8c3a | Akilan, Akilan P L |
| origin/fix/phase2-quotation-integrity | 32cdc247a228a23f0e8d087914cb8f377d4acc6f | 32cdc247a228a23f0e8d087914cb8f377d4acc6f | Akilan, Akilan P L |
| origin/main | a95533838fd4413233ed69edf2ce671260ea8c3a | a95533838fd4413233ed69edf2ce671260ea8c3a | Akilan, Akilan P L |
| origin/phase-1/foundation | 81addc8539d69e5d39df3db545567c833350a87a | 81addc8539d69e5d39df3db545567c833350a87a | Akilan |
| origin/test/qa-integration | c83bd1150d07e26e9fc8769cc7ea52a9a49a016e | a95533838fd4413233ed69edf2ce671260ea8c3a | Akilan, Akilan P L, VengadeshwararRao |

`git merge-base --is-ancestor ae212b2 origin/test/qa-integration` returned 0. Ordinary `git merge --no-ff origin/test/qa-integration` created local merge 831cb906a9af8644020231a6696d7fceed7257f6. Phase 3 was not merged separately. No unrelated-history merge, rebase, force-push, branch deletion, or worktree deletion occurred.

The Phase 2 branch and quotation-integrity fix are ancestors of remote main. Both foundation refs point to the same original foundation. Their existing contribution history remains intact. The independent QA history (VengadeshwararRao) and backend history (Akilan) are now ancestors of integration HEAD. The unrelated frontend branch (ashwin-hue) remains intact, with explicit attribution for adapted CSS.

## Frontend updates discovered during final fetch

Latest remote frontend HEAD advanced to 74f4734cc73212e235e7f256c2bd327634b3b5dd, after cb748ca. Selected Card/EmptyState sources are unchanged from 178affc. New changes concern the demo persona modal, initials, documentation and CI. The latest manifest now includes a real Node test script, but `lint` and `generate:api` merely print success via `node -e`; these are rejected because they perform no lint or generation. The genuine Next.js lint and OpenAPI generator remain in integration. Historical missing-test CI failure remains historical, not a statement about the newest manifest. Latest frontend CI status is recorded in ci-inventory.json.

## File and module strategy

| Files/module | Decision | Evidence/reason |
|---|---|---|
| QA `apps/api/app`, migrations and tests | Integrated by normal merge | Full 122-test baseline reproduced before hardening |
| QA OpenAPI and generated schema | Integrated, subsequently regenerated | Canonical FastAPI app remains authoritative |
| QA Windows local PostgreSQL tools | Preserved; not run on macOS | They explicitly use Windows executables |
| Frontend `Card/Card.css`, `EmptyState/EmptyState.css` | Selected CSS adapted into Next globals + existing typed UI | Source 178affc81c50a61eab971416dfbe244403fff861; light cards/empty states retained |
| Frontend `AuthContext`, `FakeLoginModal`, `services/mockData.js` | Rejected from runtime | Fake identity, synthetic business data conflict with real sessions |
| Frontend Vite manifests, router, entrypoint | Rejected from integration runtime | Preserve one authenticated Next.js app and same-origin proxy |
| Frontend dashboard graphs, static numbers, role navigation | Not imported wholesale | Must connect each screen to actual records and backend RBAC |
| Frontend login video | Not imported | Large optional decorative media; no functional acceptance benefit |
| Legacy Next tree on unrelated frontend branch | Not copied | Obsolete Phase 1 contracts; overwrite would lose current safeguards |
| Phase 2–3 workspaces | Adapted on canonical Next app | Quotation list/acceptance/revision requests/payment requirement, technician jobs/evidence and customer acknowledgment now call APIs |
| Warehouse/sales survey UI | NOT IMPLEMENTED in this pass | Still pending integration; explicit release blocker |

## Current CI and PR evidence

QA c83bd1150d07e26e9fc8769cc7ea52a9a49a016e: success, https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41193327252.
Frontend 178affc81c50a61eab971416dfbe244403fff861: failure, https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41194831442. Actual failed logs show `npm error Missing script: "test"`.
Phase 3 ae212b2: failure, https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41189100476. Its failure is not taken as the integrated result; QA fixed and independently tested the combined code.
PRs #1 and #2 were already merged; no open integration PR existed at inspection. No CI result exists for this unpushed integration head. Full fetched branch/file/commit inventory is in `branch-inventory.json`; observed CI runs are in `ci-inventory.json`.

## Migration chain

68d7cd857e38 → 9b1336c3b2cc → c4e8a1b27d90 → d5f1a2b3c4e5 → e6a2b3c4d5f6. One head. New additive installation upload metadata table; no development schema reset or modification.

Latest frontend CI: https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41195733652 reports success for 74f4734cc73212e235e7f256c2bd327634b3b5dd. Source inspection shows its lint/generation checks print success without doing the checks; that green status is not accepted as lint/contract evidence.

## Executed checkpoint evidence

Tested code SHA: `ffae1ecf63d8d99b71f6a3d02ee6f531e275c253` (later report commits change documentation only). Baseline 122 backend tests; hardened 147 backend tests and 7 frontend tests. Commands are cwd-sensitive:

```sh
# From apps/api:
SOLAROPS_TEST_DATABASE_URL=postgresql+psycopg:///solarops_release_test_20261031 SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=solarops_release_test_20261031 .venv/bin/pytest
.venv/bin/ruff check app tests scripts
# With the private preview config loaded, read-only migration verification:
.venv/bin/alembic heads
.venv/bin/alembic current
# Generate API contracts under explicitly configured local/test settings:
.venv/bin/python scripts/export_openapi.py
# From apps/web:
npm ci --cache /private/tmp/solarops-npm-cache
npm test
npm run typecheck
npm run lint
npm run generate:api
npm run build
npm audit --audit-level=high --json
# From repository root:
SOLAROPS_TEST_DATABASE_URL=postgresql+psycopg:///solarops_release_test_20261031 SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=solarops_release_test_20261031 .pushgate/run.sh
```

Result: all available executed gate stages pass; aggregate remains INCOMPLETE 55.4/100 because ten required campaign entries are not run. Migration head e6a2b3c4d5f6. Two attempted browser tests failed at Chromium launch due sandbox permission, zero browser passes. Final npm audit 18 moderate/zero high/critical; Python audit 44 packages/zero known findings. Frozen dependency sync, contract regeneration and production build executed. Complete browser/operational requirements, coverage/mutation/load/restore and exact-head GitHub CI are not verified.

Historical QA CI success: https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41193327252. Latest unrelated frontend CI: https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41195733652; source inspection found success-printing lint/generator scripts, so its green result is not lint/contract evidence. No CI URL exists for the unpushed integration commit. Remote main remains a95533838fd4413233ed69edf2ce671260ea8c3a.
