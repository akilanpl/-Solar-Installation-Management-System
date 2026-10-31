# SolarOps Phase 3 backend QA and regression report

Date: 2026-10-31 (Asia/Calcutta). Repository: `akilanpl/-Solar-Installation-Management-System`. QA checkout: `qa-checkout`; branch: `test/qa-integration`.

**Verdict: QA executed; Phase 3 acceptance FAILS. Final backend run: 119 passed / 3 failed. Chromium: 3 passed / 1 failed. Migration, isolation, lint, types, build and generated-contract checks passed. The failing tests remain enabled; no production security or business rule was relaxed.**

## Integration history and scope

Starting QA commit: `7b0e80742e47c3b612e455a8839b138061760320`. A full fetch of remote branch heads established the actual backend source:

- `origin/feature/phase3-warehouse-installation`: `ae212b2cdfce755b69ec9a73df15f3907873bf0d`.
- `2e4ec90`: initial Phase 3 inventory/delivery/installation/warranty implementation.
- `ae212b2`: acceptance-audit corrections for ledger deduction, component locks, serial assignment and foreign technician visibility.
- Required ancestors: Phase 2 workflow `b979ec6`, quotation/order integrity `32cdc24`, integrated through `8423f9b` and `a955338`.
- Ordinary non-fast-forward merge: **`aba0169ca6d6da80ef36ff29b695b7916e3a170c`**, parents `7b0e807` and `ae212b2`. Merge completed without conflicts. Backend changes remain attributable to their original authors.

Later frontend redesign/bypass-login commits belong to a separate branch and were not integrated. The backend branch brings Phase 2 prerequisites plus Phase 3, not a completed Phase 3 frontend. The source team's verification report was treated as historical evidence, not a substitute for local execution.

## Environment and database protection

Reused the existing Windows 11 x64 checkout, CPython 3.14, Node 24, portable PostgreSQL **16.15** on **127.0.0.1:55432**, and existing locked environments. `uv sync --frozen` added the source's locked `python-multipart` dependency. Phase 2 also adds GST/advance/quotation-validity/evidence configuration; no new Phase 3 external provider or worker was discovered.

| Database | Before | After QA | Result |
| --- | --- | --- | --- |
| `solarops_dev` | 13 tables, 27 indexes, revision `68d7cd857e38` | Same schema revision/counts; same protected data fingerprint | PASS — no migration, reset, seed or browser write |
| `solarops_test` | Original Phase 1 schema | 44 tables, 104 indexes, revision `d5f1a2b3c4e5` | PASS — disposable schema repeatedly rebuilt/migrated |

Different owners/passwords remain configured. A real test-role CONNECT attempt to development was denied. Before/after fingerprints covered user identity/role, enquiry identity/reference/status/ownership/site and history rows. Counts remained **16 users, 8 enquiries, 14 history rows**. This proves preservation of those records/columns, not a full binary database backup.

The old development API/frontend were already running on loopback ports8000/3000 and were not reused for Phase 3 tests. The merged test API/frontend started successfully on **8001/3001**, with readiness checking the actual test database. Browser servers stopped after execution; PostgreSQL and original demo processes were left alone. The development schema is intentionally old: do not restart the merged API against it expecting Phase 3 functionality until a separately authorized development upgrade.

Browser QA uses `scripts/run_browser_qa.py`: it checks local `solarops_test`, calls the existing guarded test migration reset, and prepares preverified QA accounts there using ignored local credentials. `playwright.qa.config.ts` rejects a development database URL, refuses server reuse, points the same-origin proxy to8001 and uses `.next-qa` output. The existing demo build directory and development mailbox are not reused. Test API development mode only enables its isolated local mailbox; normal login, CSRF and RBAC remain active. Pytest and browser QA run sequentially because both own the disposable database.

## Migration verification

Single chain, no competing heads:

```text
68d7cd857e38  Phase 1 identity/enquiry/catalogue
  -> 9b1336c3b2cc  Phase 2 survey/quotation/payment/order
  -> c4e8a1b27d90  one active quotation and one order per enquiry
  -> d5f1a2b3c4e5  warehouse/delivery/installation/warranty
```

New upgrades were inspected before execution. Pytest reached head from an empty test public schema. `test_migrated_schema_matches_current_sqlalchemy_metadata` found no Alembic/ORM metadata differences. `test_phase3_round_trip_keeps_existing_phase1_record` created an actual customer enquiry, downgraded only test to `c4e8a1b27d90`, then upgraded again; the record survived. New table foreign keys, ledger indexes, serial uniqueness and quantity checks were inspected. The broader source tests exercise real constraints and rollback.

That round-trip does not certify downgrading a populated production Phase 3 database. Downgrade deliberately drops Phase 3 tables; this was safe only in the named disposable test database. No development migration was attempted. `check_local_db.py` now requires current head for test while accepting a valid historical development revision, so a test upgrade cannot silently demand a development upgrade.

## Actual feature inventory

Backend paths below are relative to `apps/api/app`. Schemas for Phase 3 are in `schemas/phase3.py`, models in `models/phase3.py`, persistence transactions in `db/session.py:get_db`, audit insertion in `repositories/queries.py:add_audit`. There are **32 Phase 3 endpoint operations** in the live OpenAPI document.

| Feature | Routes/source | Endpoints under `/api/v1` | Roles enforced by service | Tables | Rules/errors | Coverage and gaps |
| --- | --- | --- | --- | --- | --- | --- |
| Stock operations/ledger | `api/v1/warehouse.py`; `services/inventory_service.py` | GET `/stock`; POST `/stock/operations`; GET `/{id}` and POST `/ready`, `/validate`, `/cancel` beneath operations | Warehouse staff/manager/admin write; those roles plus sales read | `stock_operations`, `stock_operation_lines`, `stock_ledger`, `warehouse_locations`, catalogue components, counters/audit | Draft→ready→done; Decimal quantities; source/destination checks; negative stock denied; component/operation locks; unknown component/location400, missing record404, bad transition/conflict409 | Source receipt/transfer/adjustment/concurrency tests; new five invalid-write rollback cases, mass assignment/UUID and auth/CSRF tests. Full role matrix not exhaustive. |
| Reservations | Same warehouse route/service plus order service | POST/GET `/stock/reservations` | Sales/admin/warehouse roles | `stock_reservations`, orders/order lines | Confirmed order auto-reserves; unique order/component; reserved→consumed on handover | Source reservation and competing-order tests; new threshold service test accounts for reserved stock. Release/cancellation recovery is not a complete new workflow. |
| Equipment serials | Warehouse route; inventory/fulfillment services | POST `/serials/scan`, `/serials/{id}/assign` | Warehouse staff/manager/admin | `equipment_serials`, catalogue, operations, orders | Uppercase serial uniqueness; reject done-operation attachment; component/order match; installed on delivery confirmation | Source serial uniqueness/assignment/mismatch/install tests passed. No invented serial-level picking UI. |
| Replenishment | Warehouse route; inventory service | POST `/replenishment/requests`, `/{id}/decision` | Warehouse request; manager/admin decide | `replenishment_requests`, ledger/reservations | Positive quantity; one approve/reject decision; staff decision403, repeated decision409 | Source manager boundary test passed; new internal `threshold_suggestion` arithmetic/non-write test passed. Suggestion helper has no public API route here; approval does not automatically receive stock. |
| Picking/deliveries | Warehouse route; `services/fulfillment_service.py` | POST/GET `/deliveries`, GET `/{id}`, POST `/transit`, `/deliver`, `/confirm`, `/cancel` | Warehouse writes; technician also confirms; staff read globally; customer reads own order's delivery | deliveries/lines, stock operations/ledger, reservations, orders, serials/audit | MAIN-only atomic pick; other-order reservations respected; idempotent create; cancellation restocks; insufficient stock409 | Source concurrency/cancel/confirmation tests and new retry/different-valid-body conflict/foreign-customer tests passed. No partial delivery/returns or multi-location allocation. |
| Installation scheduling/recommendations | `api/v1/installation.py`; `services/installation_service.py` | POST `/scheduling/installations/{id}/slot`, `/assignments/recommendations` | Sales/admin | scheduling requests, users/profiles, jobs | Timezone-aware slots; active technicians ranked by open jobs; five-or-more omitted | Source slot/permission checks passed. No skill matrix, geographic match or customer self-scheduling. |
| Technician jobs | Installation route/service | POST/GET `/jobs`; GET `/{id}`; POST `/en-route`, `/arrival`, `/customer-otp`, `/evidence`, `/signature`, `/completion` | Sales/admin manage; assigned technician executes; customer reads own; operational staff read according to service policy | `installation_jobs`, `installation_otps`, scheduling requests, orders/users/audit | One job/order, single-use expiring code, evidence/signature gates; foreign technician404 | Source happy path/expiry/reuse/foreign technician passed; new ownership/no-code-repeat passed. Three new gate tests FAIL: lockout persistence, inactive assignment, arrival prerequisite. |
| Warranty | Installation route; fulfillment service | GET `/warranties/order/{id}`, POST `/{id}/void` | Operational staff and owner customer read; support/admin void | `warranties`, orders, customer users/audit | Activate at delivery confirmation; active→void guarded; one/order | Source activation/void/replay passed; new foreign customer warranty404 passed. No separate support complaint/repair module implemented. |

Phase 2 prerequisites are real implemented modules: survey assignment/submission/approval/evidence; BOM/pricing and versioned quotation acceptance/revision; sandbox/cash payments and confirmed orders with warehouse/scheduling handoff. `tests/test_phase2_workflow.py`, `test_quotation_integrity.py` and `test_pricing.py` execute **22 passing cases**. No real payment provider was invoked.

## Test inventory and exact results

Before adding independent tests, the preserved Phase 1 **56** cases passed; then all **99** existing integrated cases passed after applying the QA database marker to imported DB-dependent modules. The marker adaptation retains isolation and puts the imported tests in `-m database`; it does not skip them. Imported test settings raise login limits for multi-role workflow fixtures only; explicit limit tests still set isolated low limits and pass.

Final results, measured from execution/JUnit:

| Suite/check | Passed | Failed | Error/skip/blocked | Evidence |
| --- | ---: | ---: | --- | --- |
| Non-database backend | 25 | 0 | 0 / 0 / 0 | 2.96s JUnit; runtime21 + pricing4 |
| PostgreSQL backend | 94 | 3 | 0 / 0 / 0 | 97 executed, 105.03s JUnit |
| Full backend | **119** | **3** | **0 / 0 / 0** | 122 executed, 86.65s |
| Preserved Phase 1 subset within full | 56 | 0 | 0 | Original six modules/cases unchanged in intent |
| Phase 2 prerequisite subset within full | 22 | 0 | 0 | Workflow13 + pricing4 + integrity5 |
| Backend team's Phase 3 subset within full | 21 | 0 | 0 | Existing warehouse/install tests |
| New independent Phase 3/migration subset within full | 20 | 3 | 0 | QA regression21 + migration2 |
| Frontend Vitest | 7 | 0 | 0 | Two files, 841ms |
| Chromium existing regression | 3 | 1 | 0 | Four executed, 50.2s |
| Ruff lint / formatter | PASS | — | — | 77 files formatted at final check |
| Compile / types / ESLint / production build | PASS | — | — | 26 pages; isolated `.next-qa` output |
| Live OpenAPI JSON comparison | PASS | — | — | Export matches backend source contract |
| Generated TypeScript reproduction | PASS | — | — | Generated twice; hashes identical |
| Development snapshot / role separation / frozen test1 report | PASS | — | — | Rechecked after test resets/browser |

Subsets and marker runs overlap the full run; do not sum them into additional unique tests. There are **122 distinct backend cases**. The three failures are the same defects in marker/full executions. No xfail or broad skip was added. The generated TypeScript originally lacked Phase 3 endpoints despite the JSON including them; regeneration was retained (3065 added/1173 removed lines versus the integrated source's generated file). This is a real contract update, not line-ending noise.

Neither coverage.py nor pytest-cov was installed. No dependency was added only for a percentage, and **no line or branch coverage percentage is claimed**. Counts show exercised cases, not completeness. Security coverage includes actual backend roles/ownership, CSRF, invalid UUID/extra fields, retry/rollback and scoped secret-response checks; it is not an exhaustive per-endpoint role/mass-assignment/status-contract matrix.

## Defects with reproduction and proposed corrections

### P3-001 — High: installation wrong-code attempts do not persist

- Component: `services/installation_service.py:verify_customer_otp`, request transaction `db/session.py:get_db`.
- Reproduce: `uv run pytest tests/test_phase3_qa_regression.py::test_customer_otp_wrong_attempts_persist_and_lock_after_five -vv --tb=short`.
- Preconditions: confirmed order, created job, normally authenticated assigned technician and valid CSRF. Submit five incorrect codes, inspect saved attempt count, then submit a sixth incorrect code.
- Expected: saved attempts5; sixth request409 `otp_locked`.
- Actual: saved attempts0; sixth request400 `invalid_customer_code`. The assertion reports only these non-secret values.
- Root cause: increment is flushed, then `AppError` is raised; the outer dependency rolls the transaction back. The documented five-attempt lock cannot accumulate across requests.
- Proposed correction: deliberately persist the failed security counter in an appropriate transaction boundary, as Phase 1 email verification does, without committing unrelated work or weakening the lock. Keep this regression.
- Status: verified repeatedly; **not fixed**. Threat scope requires a caller permitted to execute the job; this is not an anonymous endpoint.

### P3-002 — Medium: inactive technician accepted for job assignment

- Component: `installation_service.create_job`.
- Reproduce: `uv run pytest tests/test_phase3_qa_regression.py::test_inactive_technician_cannot_be_assigned_to_a_new_job -vv --tb=short`.
- Expected: reject inactive technician400 before creating job/OTP rows.
- Actual:201 Created for a stored technician with `is_active=False`.
- Root cause: lookup validates existence and technician role, but omits the active flag despite its error message describing an active technician. Such an employee cannot normally sign in to execute the assigned job.
- Proposed correction: check active state before writes, retain role and ownership checks, and rerun job/assignment regressions.
- Status: verified; **not fixed**.

### P3-003 — Medium: completion bypasses recorded arrival

- Component: `installation_service.complete_job` and documented installation state machine.
- Reproduce: `uv run pytest tests/test_phase3_qa_regression.py::test_completion_requires_recorded_arrival_even_after_otp_evidence_and_signature -vv --tb=short`.
- Complete OTP/evidence/confirmed-signature steps without calling arrival.
- Expected:409; job remains en_route without arrival. Documented flow requires the on-site step before completion.
- Actual:200; PostgreSQL saves status completed with `arrival_at` null.
- Root cause: completion checks OTP/evidence/signature and terminal states, but no on-site/arrival prerequisite. Earlier evidence/signature recording is allowed, so those checks cannot establish arrival.
- Proposed correction: enforce the intended on-site/arrival gate before the completion state change and audit insert. Do not invent a client-supplied arrival timestamp.
- Status: verified; **not fixed**.

### P3-004 — High integration blocker: sales UI cannot submit the new qualification prerequisites

- Component: `apps/web/src/app/sales/enquiries/[id]/page.tsx` versus `services/enquiry_service.py:qualify_enquiry` and `schemas/QualificationUpdate`.
- Reproduce: from `apps/api`, `uv run python scripts/run_browser_qa.py`; the seeded customer/sales scenario fails. The original signup/under-review scenario, admin scenario and login smoke pass.
- Expected: a sales user can supply the required shadow-free area and grid suitability, qualify, and let the customer see the persisted result after re-login/reload.
- Actual: PATCH qualification422; the form sends only status/note and offers no area/grid inputs. The browser test stops at that failure; its later qualified-status/relogin steps were not executed in this cycle.
- Root cause: Phase 2 strengthened backend qualification, while this backend branch retains the Phase 1 UI. The JSON/types now document the fields, but UI flow was not adapted.
- Proposed correction: frontend owner adds validated area/grid inputs and sends them. Do not remove backend prerequisites or change the browser test to a weaker status merely to obtain green.
- Status: real browser reproduction; **not fixed**.

### QA-FLAKE-001 — Historical email verification flake remains open

The earlier intermittent correct-email-OTP rejection did **not recur in the executed Phase 3 runs**. Safe failure diagnostics remain. Its root cause is still unestablished, so it is not marked resolved. It is a separate issue from deterministic P3-001, which concerns installation OTP attempt persistence.

## Debugging and QA corrections made

- One initial delivery retry assertion expected conflict409 for a nonexistent order, but the service correctly checks order existence first and returns404. The revised test uses a second valid order; its409/replay/no-extra-ledger assertions passed. This corrected the input rather than relaxing intended retry behavior.
- Added database markers to three imported modules so existing cleanup applies and marker selection is truthful. Source tests themselves retain their business assertions.
- Ruff found17 imported files needing formatting and two extra EOF blank lines. Formatting was applied, not business logic changes. An AST comparison confirmed all **14 changed production Python files are structurally identical to the merged backend source**. The other formatting changes concern imported tests and their new markers.
- Updated test migration verification to allow development's historical revision while requiring test's current head. Added guarded browser test database bootstrap and separate ports/build directory.
- Regenerated missing Phase 3 API types. Next's generated `next-env.d.ts` directory reference was restored; deliberately configured `.next-qa` output and types inclusion remain.
- Failed read-only inspection commands caused by an incorrect working directory/PowerShell quoting were corrected or abandoned; they performed no database writes.

No substantial product fix, authentication bypass, weakened CSRF/OTP/RBAC control or missing product feature was introduced. The failures belong to the responsible backend/frontend owners; proposed changes above are not claimed implemented.

## Reproduction commands

From `apps/api` in the existing checkout, with ignored local config/credentials from `LOCAL_POSTGRESQL.md`:

```powershell
uv sync --frozen
uv run alembic heads
uv run alembic history
uv run python scripts/check_local_db.py record
uv run pytest -m 'not database' -vv --tb=short --show-capture=no --junitxml=../../var/phase3-runtime.xml
uv run pytest -m database -vv --tb=short --show-capture=no --junitxml=../../var/phase3-database.xml
uv run pytest -vv --tb=short --show-capture=no --junitxml=../../var/phase3-full.xml
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run python -m compileall -q app tests scripts
uv run python scripts/export_openapi.py
git diff --exit-code -- ../../contracts/generated/openapi.json
uv run python scripts/check_local_db.py verify
uv run python scripts/run_browser_qa.py
uv run python scripts/check_local_db.py verify
```

Do not run plain `alembic upgrade head` in the development-configured shell as part of this QA procedure. Tests/the browser runner set and guard the test target explicitly. Do not run browser QA concurrently with pytest. JUnit and browser artifacts are ignored and may contain sensitive request data; they are not committed. Command history and outcomes are appended to `QA_ACTION_LOG.txt`.

From `apps/web`:

```powershell
npm test
$env:SOLAROPS_NEXT_DIST_DIR='.next-qa'
$env:NEXT_TELEMETRY_DISABLED='1'
npm run typecheck
npm run lint
npm run build
npm run generate:api
```

After the intentional API regeneration, a second generation produced the same file hash. Typecheck, lint and build were run again against the regenerated types and passed. The main task fetched all remote heads using `git fetch origin --prune 'refs/heads/*:refs/remotes/origin/*'` and merged only the verified backend branch.

## Reports, reviewer explanation and remaining risks

Created root `test 3 report.txt` and this report; appended the action log and Phase 3 explanations to `TESTING_EXPLAINED.md`. **`test 1 report.txt` is byte-for-byte unchanged**, SHA256 `DB54A48B965D1D6CD9DDBDC754D27023CDF36B385DE694729E9E9FD949BDE41E`. Historical Phase 1 result reports were not overwritten.

For the reviewer: FastAPI authenticates the cookie, enforces CSRF and validates a Pydantic payload; services enforce persisted roles and business transitions; SQLAlchemy flushes rows within a request transaction; PostgreSQL enforces constraints; `get_db` commits a successful request or rolls back a failed one. A receipt becomes stock only after warehouse validation writes the ledger. Delivery picking deducts stock atomically and confirmation activates warranty. Tests prove both the successful cross-phase path and independent rejection/rollback behavior. P3-001 illustrates why flushing before raising does not persist a failed security attempt; P3-003 illustrates why a happy-path test cannot prove every prerequisite is enforced.

Unverified/nonimplemented: complete Phase 3 UI journeys; exhaustive role/state/input combinations; production SMTP/payments; geographic/skill ranking; customer self-scheduling; procurement auto-receipt; partial deliveries/returns; populated production downgrade; live deployment, remote CI and code coverage percentages. Original development schema remains unmigrated by design. New merged API functionality is verified against test, not against that old development schema.

## Acceptance checklist

| Requirement | Status |
| --- | --- |
| Verified backend source and history-preserving integration | PASS |
| Existing QA branch/tests/history preserved | PASS |
| Clean test migration to one head; metadata parity; round-trip with Phase1 record | PASS |
| Development records and schema protected | PASS |
| Preserved Phase1 backend regression56 | PASS |
| Imported Phase2/Phase3 existing regression43 | PASS |
| New independent tests | FAIL —20 passed/3 failed |
| Installation failed-OTP lockout | FAIL |
| Active technician assignment gate | FAIL |
| Arrival-before-completion gate | FAIL |
| Existing browser regression | FAIL —3 passed/1 failed |
| New Phase3 UI journeys | NOT APPLICABLE — UI not implemented in this source |
| Frontend units/types/lint/build and backend lint/format/contracts | PASS |
| Historical email-OTP flake root-cause resolution | BLOCKED — not reproduced; remains open |
| Historical test1 artifact preserved; separate test3 reports | PASS |
| Code coverage percentage | NOT APPLICABLE — not measured |
| Push | BLOCKED pending fresh explicit user authorization; no push attempted |

Reporting status: source merge is committed as `aba0169`; final QA artifact commit SHA and clean-tree status are supplied in chat after local commit. No merge into main or force push occurred.
