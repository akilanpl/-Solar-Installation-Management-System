# SolarOps Phase 1 QA baseline

Historical baseline before local PostgreSQL setup. See [the PostgreSQL integration report](PHASE1_POSTGRESQL_INTEGRATION_REPORT.md) for subsequent executed results and resolved blockers.

Date: 2026-10-31 (Asia/Calcutta). Repository: `akilanpl/-Solar-Installation-Management-System`. QA branch: `test/qa-integration`, cloned from `81addc8539d69e5d39df3db545567c833350a87a` into `qa-checkout` because the supplied outer directory was a source export without Git metadata.

**Partial baseline: the independent checks pass, but PostgreSQL integration is blocked. Do not treat this as Phase 1 acceptance.**

## Repository assessment

- Backend: FastAPI application factory `apps/api/app/main.py:create_app`, Pydantic v2 and pydantic-settings, synchronous SQLAlchemy sessions, psycopg, Alembic, Uvicorn; pytest/TestClient/HTTPX and Ruff. Locked dependencies installed with `uv sync --frozen`. This machine selected Python 3.14.0, permitted by `requires-python >=3.12`; Python 3.12 was not separately verified.
- Database: PostgreSQL URLs in `.env.example`; Compose offers PostgreSQL 16 on localhost:5432 and a persistent development volume. `app/db/session.py` supplies one session per request, commits successful requests, rolls back exceptions, and sets UTC. Models use UUID keys, foreign keys, unique and check constraints. Revision `68d7cd857e38` creates identity, enquiries, catalogue and audit tables, then seeds roles/packages. No migration was successfully applied here.
- Authentication: Argon2id password hashes; HMAC-digested OTP/session tokens; HTTP-only session cookie; server-side roles; double-submit CSRF with supplied-Origin checks. Test email adapter is in memory. Development mailbox is unavailable in test/production. Rate limiter is process-local and documented as unsuitable for multiple workers without a shared limiter.
- Frontend: Next.js 15 App Router, React 19, TypeScript, Tailwind, generated OpenAPI types, same-origin API proxy. Executed on Node 24.13.0/npm 11.6.2; README asks for Node 22+. Vitest and Playwright are already configured.
- Implemented modules: customer registration/verification/login/logout; employee login and admin provisioning/listing; authenticated package catalogue; customer enquiry creation/list/detail; sales/admin qualification with history/audit. Sales/admin visibility is global across enquiries; other staff roles cannot access enquiries. Survey, quotations, stock, payments, weather and support workflows are future boundaries, not verified features.
- Existing coverage: 24 PostgreSQL-fixture-dependent backend cases (auth 11, enquiries 8, health 5), 7 frontend unit cases and 1 full browser workflow. Added 20 independent ASGI/config/contract cases, 7 PostgreSQL regression cases, 1 login browser smoke and explicit CI TypeScript checking.
- Existing CI starts PostgreSQL 16, creates `solarops_test`, runs Ruff/pytest, exports OpenAPI and compares it, then installs/checks/builds the web app. It does not run Playwright. CI execution on GitHub has not been observed in this session.

## Implemented endpoint inventory

| Method | Path under `/api/v1` |
| --- | --- |
| GET | `/health`, `/ready`, `/auth/csrf`, `/auth/me` |
| POST | `/auth/signup`, `/auth/verify-email`, `/auth/resend-verification`, `/auth/login`, `/auth/logout` |
| GET, POST | `/enquiries` |
| GET | `/enquiries/{enquiry_id}` |
| PATCH | `/enquiries/{enquiry_id}/qualification` |
| GET | `/packages` |
| GET, POST | `/admin/employees` |
| GET | `/dev/mailbox/{email}` (only successful in development without SMTP) |

FastAPI also serves `/docs` and `/openapi.json`. No enquiry DELETE endpoint exists.

## Execution summary

| Check | Actual result |
| --- | --- |
| Backend discovery | 51 cases: 20 runtime + 31 database |
| Complete backend run | **20 passed, 31 setup errors**, 1 deprecation warning, 4.90s; zero assertion failures, zero skips |
| Runtime-only backend run | **20 passed**, 31 deselected, 2.59s |
| PostgreSQL integration bodies | **0 executed**; all 31 blocked before test bodies by migration connection setup |
| Ruff lint / format | PASS; 43 files already formatted at final check |
| Python compileall | PASS for app/tests |
| Vitest | **7 passed**, 2 files |
| TypeScript / ESLint | PASS; also checked during successful production build |
| Next.js production build | PASS, 26 pages generated; initial sandbox EPERM resolved by approved elevated retry |
| Live OpenAPI vs committed JSON | PASS through runtime test |
| Generated TypeScript vs committed file | PASS; `npm run generate:api` followed by `git diff --exit-code` |
| Playwright discovery | 2 tests: login smoke and customer-to-sales workflow |
| Browser login smoke | **1 passed**, 13.0s, Chromium; checks rendered login, portal switching, password type and no page errors |
| Full customer-to-sales browser workflow | BLOCKED, not executed: requires reachable development PostgreSQL, migrations and seeded sales account |

Initial sandboxed installs and ASGI/browser runs hit cache, socket or filesystem permissions. Approved elevated retries installed dependencies, executed runtime tests and built the frontend. The original elevated PostgreSQL retry timed out after 130.87s. The final full run used `connect_timeout=2` and still failed database setup. Docker and psql were absent on PATH and no `C:\Program Files\PostgreSQL` installation was found. A service query was denied in the sandbox, so absence of all possible PostgreSQL installations is not asserted.

## Results by category

| Category | Status and evidence |
| --- | --- |
| Startup/environment | PASS: application factory, docs, health and controlled missing settings tested; Uvicorn and Next started in Playwright |
| Health/readiness | PASS for independent liveness and real unavailable-database 503; healthy-database readiness BLOCKED |
| Authentication/sessions | Anonymous 401 boundary PASS; signup/OTP/login/logout persistence BLOCKED |
| Authorization | Anonymous protected reads PASS; authenticated ownership, customer vs sales and role escalation checks BLOCKED |
| Enquiries | CRUD subset/qualification/history/idempotency tests present; persistence and customer-to-sales flow BLOCKED |
| API validation | Invalid signup, forbidden role field, CSRF cases, safe errors, unknown route and unsupported method PASS; authenticated enquiry validation BLOCKED |
| Database | Guard rejects non-test names PASS; clean migration, constraints and rollback BLOCKED |
| Basic security | CSRF/anonymous/role-field rejection/error sanitization/mailbox hiding PASS; persisted session revocation and endpoint rate limiting BLOCKED |
| Frontend/contracts | Unit tests, types, lint, build and contract comparisons PASS |
| Browser E2E | Login smoke tracked separately; complete persisted workflow BLOCKED |

## Findings and corrections

### ENV-001 — High verification blocker: PostgreSQL unavailable

- Component: local test infrastructure, not an established product defect.
- Reproduce: from `apps/api`, set the local test URL with `connect_timeout=2` and run `uv run pytest --tb=short`.
- Expected: connection to the disposable `solarops_test`, clean Alembic upgrade and test execution.
- Actual/evidence: `sqlalchemy.exc.OperationalError` wrapping `psycopg.errors.ConnectionTimeout`; 31 setup errors. Initial sandbox attempt had socket permission denied; approved elevated retry still timed out.
- Root cause: no reachable PostgreSQL at configured localhost:5432; precise service/firewall cause not established.
- Status: BLOCKED. No shared development database was reset; fixture did not reach DROP SCHEMA.

### QA-001 — Medium: independent checks depended on destructive DB fixture

- Component: `apps/api/tests/conftest.py:clean_database`.
- Reproduce before change: run even the existing health/outage/provider tests without PostgreSQL.
- Expected: independent checks can run without database setup; integration checks still require a real database.
- Actual/evidence: global autouse cleanup requested the session application fixture, which attempted a schema reset before every test category.
- Root cause: unconditional autouse dependency.
- Correction: database marker controls cleanup; all existing integration modules remain marked; runtime tests use an isolated real ASGI application. Default pytest still runs both categories and fails visibly if PostgreSQL is unavailable.
- Status: independent suite verified with 20 passes; PostgreSQL cleanup path still requires integration verification.

### QA-002 — Low: invalid OTP input could equal the valid code

- Component: `apps/api/tests/test_auth.py:test_invalid_otp_fails`.
- Reproduce before change: if random OTP equals `000000`, the test submits the correct code while expecting failure.
- Expected: wrong-code test always uses a code different from the captured OTP.
- Actual/evidence: hard-coded `000000`; `core/security.py:new_otp` permits all six-digit combinations.
- Correction: select `000000` unless it is the actual code, otherwise `111111`.
- Status: corrected by inspection and lint; execution BLOCKED by PostgreSQL.

### QA-003 — Low: package assertion was vacuous

- Component: `apps/api/tests/test_enquiries.py:test_packages_come_from_database`.
- Reproduce before change: inspect `all(... for item in response.json() if False)`.
- Expected: assertions inspect returned packages.
- Actual/root cause: `if False` creates an empty iterator, and `all([])` always passes.
- Correction: removed that assertion; real catalogue-code and absence-of-price assertions remain intact.
- Status: corrected by inspection; execution BLOCKED by PostgreSQL.

### QA-004 — Low: new smoke locator omitted accessible hint text

- Component: new `apps/web/e2e/smoke.spec.ts`, test implementation error during development.
- Reproduce: exact label `Employee ID` after selecting Sales.
- Expected: find the visible staff input.
- Actual/evidence: Playwright snapshot names it `Employee ID Example: EMP-SALES-001`; `TextField` nests hint text in the label.
- Correction: use textbox role with accessible-name prefix `/^Employee ID/`. No application behavior changed.
- Status: verified; final browser rerun passed (1 test, 13.0s).

No production-code defect is claimed as validated. No application runtime or migration code was changed.

## Exact reproduction commands

From this checkout's `apps/api` directory:

```powershell
uv sync --frozen
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run python -m compileall -q app tests
uv run pytest -m 'not database' -v --tb=short
# Only a clearly disposable LOCAL solarops_test database may be used here:
$env:SOLAROPS_TEST_DATABASE_URL='postgresql+psycopg://solarops:solarops@127.0.0.1:5432/solarops_test?connect_timeout=2'
uv run pytest --tb=short
```

Execution used `.venv\Scripts\python.exe -m pytest` and `.venv\Scripts\ruff.exe` directly after sync to avoid repeated sandboxed uv-cache access. Both use the synced environment. Runtime tests include live OpenAPI equality; database fixture automatically drops/migrates ONLY the named test database's public schema. Do not point it at shared infrastructure even if the database has the allowed name.

From `apps/web`:

```powershell
npm ci --no-audit --no-fund
npm test
npm run typecheck
npm run lint
npm run build
npm run generate:api
git diff --exit-code -- src/generated/schema.ts
npm run e2e -- --list
npx playwright install chromium
$env:SOLAROPS_APP_ENV='test'
$env:SOLAROPS_DATABASE_URL='postgresql+psycopg://solarops:solarops@127.0.0.1:5432/solarops_test?connect_timeout=2'
$env:SOLAROPS_SECRET_KEY='qa-browser-local-only-secret-key-32-characters'
$env:NEXT_TELEMETRY_DISABLED='1'
npm run e2e -- smoke.spec.ts
```

The browser secret shown is a published local-only QA value, not a deployment credential. The login smoke needs no seeded data. For the **unexecuted complete workflow**, follow README: configure a local development `.env`, create a separate development database, run `uv run alembic upgrade head`, `uv run python scripts/seed_dev.py`, then start `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` and `npm run dev`. In a fresh development shell, set `SOLAROPS_SEED_PASSWORD` from the ignored `var/dev-seed-password.txt` without printing it and run `npm run e2e -- enquiry.spec.ts`. Do not run that workflow with the test-mode mailbox configuration above.

## Limitations and next priorities

1. Restore local PostgreSQL connectivity; run all 31 marked cases and the empty-database migration. New PostgreSQL tests are collected/linted but remain unverified.
2. Seed a disposable development stack and execute the complete browser workflow, including persistence across reload and staff/customer identities.
3. Concurrent reference/idempotency races, parallel qualification, uniqueness violation recovery, all staff-role combinations, SQL-injection-like persisted inputs and broader response-secret assertions are not covered by newly executed tests. Sequential idempotency and ownership tests already exist but are blocked here.
4. Python 3.12, Node 22, Linux CI and production SMTP were not exercised locally. Starlette warns that its HTTPX TestClient integration is deprecated; no dependency migration was attempted.
5. CI has not been run remotely. No Playwright CI job was added because the full local persisted workflow is not verified.

## Acceptance checklist

| Foundational requirement | Status |
| --- | --- |
| Work on designated QA branch | PASS |
| Action/change log | PASS — `QA_ACTION_LOG.txt` |
| Backend imports/starts | PASS |
| Frontend starts/builds | PASS |
| Health and API documentation | PASS |
| Unavailable database readiness fails safely | PASS |
| PostgreSQL connection / healthy readiness | BLOCKED |
| Empty test database migration | BLOCKED |
| Signup / OTP / login / logout persistence | BLOCKED |
| Customer enquiry persistence and sales update | BLOCKED |
| Authenticated RBAC and customer isolation | BLOCKED |
| PostgreSQL constraints and rollback | BLOCKED |
| Independent validation/CSRF/error checks | PASS |
| Frontend unit tests, lint, types, generated contracts | PASS |
| Full browser customer-to-sales workflow | BLOCKED |
| Browser login rendering/portal switching | PASS |
| Push to confirmed QA destination | BLOCKED — user confirmation required before any push |

See `TESTING_EXPLAINED.md` for the implementation walkthrough and `QA_ACTION_LOG.txt` for actions and changes. Commit SHA and push status are reported in chat after local preparation.
