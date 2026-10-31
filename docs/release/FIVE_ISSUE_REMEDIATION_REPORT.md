# Five-issue remediation report

Status: PARTIAL. This is a checkpoint, not closure of the five categories.

| Category | Defect and root cause | Implementation and test evidence | Remaining requirements | Verdict |
|---|---|---|---|---|
| 1 Authentication/OTP | Staff received raw code on job creation; plain SHA-256 permits offline enumeration; failure committed caller transaction; email verification had the same commit coupling and no row lock | Raw code removed from every ordinary job response. Configured customer email channel used. HMAC binds code to job and purpose. Independent row-locked security sessions persist attempts/consumption without caller writes. Tests cover 5-attempt lockout, expiry, replay, cross-owner reads, two simultaneous verifications, caller rollback isolation. Email verification also uses an isolated transaction. Production configuration rejects insecure cookies/origins; forwarding headers require explicitly trusted proxy | Persistent multi-instance login throttling, broader staff lifecycle/session tests, deployment verification and broader recovery tests | PARTIAL |
| 2 Installation evidence | Arbitrary references and technician-provided customer_confirmed boolean; no file custody or acceptance integrity | Additive upload metadata table, generated storage keys, bounded upload, Pillow image validation, server upload time/actor/job, SHA-256. Authorized downloads rehash files. Evidence requires real uploaded keys, valid work interval/capacity/nonempty finite electrical readings. Owning authenticated customer reviews hashed summary then signs acknowledgment; HMAC protects payload; replay/edits rejected. QA arrival gate preserved. Completion rechecks file and acknowledgment integrity | Touchscreen signature artifact still missing (typed acknowledgment only). Electrical limits are broad application guardrails, not an approved engineering test protocol. Capacity is not yet checked against order BOM; installed serial verification and retention/backup process incomplete. File + DB atomic orphan cleanup incomplete. Legacy SHA OTPs require owning-customer code reissue through the new rate-limited endpoint; old unbound signatures fail completion | PARTIAL |
| 3 Operations | Delivery.order_id unique; MAIN-only picking; workload-only scheduling; replenishment lacks PO/receipt chain; one order-level 5-year warranty | Existing append-only ledger/stock locks, transfers, reservations, serial assignment and delivery transitions retained and exercised by baseline tests. Misleading “nearest qualified” recommendation text replaced with explicit workload-only statement | Multi-location reservation/allocation; partial dispatch/remaining quantities; inspected physical returns; supplier approval-to-PO-to-receipt; skill/hour/overlap/capacity scheduling; serial custody history and product-specific warranty terms remain NOT IMPLEMENTED | NOT IMPLEMENTED |
| 4 External capabilities | Existing local sandbox and file mailbox cannot establish live provider success | Production sandbox refuses operations; production requires configured SMTP. Installation codes sent to actual customer email through configured sender; test capture remains isolated. No real charge, SMS, supplier transaction, weather/map data or telemetry invented | Online provider adapter/webhook/refund/reconciliation not implemented; live provider credentials/capabilities unavailable; SMTP delivery status not proven by SMTP acceptance | PARTIAL |
| 5 Reliability | Insecure production cookie/origin config possible; spoofable forwarding header; uncorrelated requests; vulnerable npm dependencies | Config validators, explicit proxy trust, server-generated request ID and timing metadata, redacted database error logs; targeted Vitest/PostCSS updates. Backend/Next build checks executed. A local fail-closed push gate and CI workflow added, explicitly incomplete | Real structured log shipping, distributed throttling, staged deployment, restore rehearsal, retention, load/resilience, full security review and complete release gate campaign remain | PARTIAL |

`test_installation_hardening.py` adds observable database/HTTP/file regressions; old QA tests are preserved and adapted to receive test codes from the email capture, upload actual test images, and authenticate the customer for acknowledgment. No old regression assertion was removed to pass security checks. Migration test expected head changed to the new additive revision.

Software records evidence and authenticated acknowledgment; it cannot prove that a photo depicts the claimed physical work. No physical installation, delivery or real payment was claimed by these tests.

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
