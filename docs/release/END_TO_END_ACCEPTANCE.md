# End-to-end acceptance

Status: BLOCKED for browser acceptance; PARTIAL for API lifecycle evidence.

Existing `test_cross_phase_order_to_completed_installation` drives real HTTP services on disposable PostgreSQL through customer/signup, enquiry, survey, quotation, sandbox advance, order, stock receipt/pick, delivery and installation completion. Hardened path uploads a real test image and switches to the authenticated customer to acknowledge the hashed summary. This is test-fixture evidence only; no real financial or physical event occurred.

The full real customer-to-warranty browser workflow is NOT VERIFIED. Playwright attempted two existing tests using `playwright.preview.config.ts`: login smoke and enquiry/sales persistence. Chromium failed before page interaction because the sandbox denied `bootstrap_check_in ... MachPortRendezvousServer` (Permission denied 1100). These are two environment-blocked failures, zero browser passes. Test traces remain in gitignored apps/web/test-results. The app browser tool successfully loaded the real login page at http://127.0.0.1:3001/login; this is only a page-render observation.

No account/order/payment was inserted to bypass the business lifecycle. Preview script provisions development-only staff accounts; customers must register. No full responsive/accessibility, multi-role browser failure-recovery or customer-to-warranty acceptance completed. Existing backend tests cover many negative paths but cannot substitute for these missing browser results.

Reproduce outside the restrictive browser-launch sandbox, after preview servers and staff seed exist:

```sh
cd apps/web
# Load SOLAROPS_SEED_PASSWORD securely from var/dev-seed-password.txt without printing it.
node node_modules/@playwright/test/cli.js test --config=playwright.preview.config.ts --reporter=line
```

This command covers two existing smoke/enquiry tests, not the missing full Phase 1–3 browser journey. Complete the remaining UI workflows and add that journey before release.

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
