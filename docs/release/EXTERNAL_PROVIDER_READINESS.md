# External provider readiness

| Capability | Implemented behavior/evidence | Verdict |
|---|---|---|
| Development email | Local file mailbox and test-only capturing sender. Clearly isolated from production | VERIFIED |
| SMTP email | Configurable TLS/auth sender; errors surface; installation OTP addressed to order customer. No live SMTP test performed | PARTIAL |
| Production email without SMTP | Application refuses configuration; no mailbox fallback | VERIFIED |
| SMS | No real provider adapter/delivery receipt integration | NOT IMPLEMENTED |
| Installation customer verification | HMAC job-bound code, configured email channel, no normal staff response code, durable attempts | PARTIAL |
| Sandbox payment | Existing explicitly test-only intent/outcome; rejected in production. Local tests are not bank evidence | VERIFIED |
| Authorized cash record | Existing server-side sales/admin receipt, amount/idempotency checks; exercised only with test fixtures | VERIFIED |
| Live UPI/cards/netbanking/wallet/EMI | No configured adapter or provider test evidence. Missing server-order/webhook/refund implementation as well as credentials | NOT IMPLEMENTED |
| Maps/routing | No verified provider. Recommendations say workload only; no invented distance | BLOCKED |
| Weather | No provider or forecast records. UI must remain planned/unavailable | BLOCKED |
| Inverter telemetry | No authenticated device/provider source | BLOCKED |
| Supplier external order | No verified ordering integration or manual confirmation-to-receipt chain | NOT IMPLEMENTED |
| Public hosting | No selected authorized staging environment/configuration evidence | BLOCKED |

SMTP acceptance is not final delivery. No real payment, bulk notification, external supplier order or production deployment occurred. Provider secrets were neither read into reports nor committed.

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
