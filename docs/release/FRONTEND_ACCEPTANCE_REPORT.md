# Frontend acceptance

Status: PARTIAL.

One authoritative runtime: apps/web Next.js, React and TypeScript. No unrelated-history Vite app merge; real same-origin proxy, sessions, cookies and CSRF retained. Card/empty-state CSS adapted with attribution to ashwin-hue at frontend 178affc; unchanged in latest 74f4734. No fake login/mock business service imported. Latest unrelated-branch lint/type-generation success-printing scripts were rejected.

Implemented on real authenticated APIs: customer/sales quotation list with pagination, exact version/line items/tax/discount, customer acceptance, installation-category revision request, recorded payment requirements; technician assigned jobs/en-route/arrival/code verification, real image upload and work form/completion; authenticated customer work-summary review/typed acknowledgment and code reissue. Generated TypeScript schemas are used, including separate input/output Pydantic evidence types. Multipart requests preserve browser-generated boundaries. Loading/empty/error/pending states are implemented.

Executed: seven Vitest tests pass; TypeScript strict check, Next lint and production build pass. Initial Pydantic input/output schema split caused a typecheck/build error; consuming the generated JobEvidence-Input type fixed it and the full gate rerun passed. OpenAPI TypeScript regeneration was byte-identical (SHA256 3f4536a02f9de28b812aa8f53a3fb4d3db9601bb76f48c6b4a49c3a8bbbcafe9).

Dependency changes: Vitest 4.1.12; PostCSS 8.5.23 including Next-specific override. npm ci from updated lock succeeded. Final audit: zero high/critical, 18 moderate. New component-specific interaction/accessibility suites were not completed; the seven tests are existing access/format unit tests, not coverage of all new views.

NOT IMPLEMENTED/remaining: full sales survey/quotation generation/cash/order/scheduling UI; technician survey workspace; warehouse receipt/reservation/serial/picking/delivery/procurement interfaces; complete customer order/delivery/warranty view; revision categories/handling beyond installation requests; touchscreen signature drawing. Support/finance Phase 4 remains deliberately planned. Do not describe six fully functional role workspaces.

Browser Playwright failed to launch Chromium due sandbox permission, two environment failures and zero passes. App browser loaded actual login page. Full browser, responsive and accessibility acceptance remains unverified.

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
