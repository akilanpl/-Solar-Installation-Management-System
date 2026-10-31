# SolarOps PostgreSQL integration verification

Date: 2026-10-31 (Asia/Calcutta). Repository: `akilanpl/-Solar-Installation-Management-System`; branch: `test/qa-integration`. Work continues from local commit `a6698c7`. The Git checkout is the workspace's `qa-checkout` directory; the outer source export is not the working repository.

**Verdict: PostgreSQL infrastructure is unblocked, demo data is seeded, and all final acceptance checks passed. One intermittent OTP test-setup failure remains open for investigation; a green rerun does not establish its root cause or resolution. No push was performed.**

## Installation and connection verification

- Windows 11 Home Single Language, x64, build 10.0.26200. Python 3.14.0, uv, Node 24.13.0 and npm 11.6.2 were available. Docker/psql were not on PATH. Approved service/listener/package inspection found no PostgreSQL/Docker service, existing PostgreSQL 16 winget package or listener on ports 5432/55432.
- Used a portable, user-scoped PostgreSQL **16.15** binary distribution from [EDB's official archives](https://www.enterprisedb.com/download-postgresql-binaries), linked by [PostgreSQL's Windows downloads page](https://www.postgresql.org/download/windows/). Downloaded `postgresql-16.15-1-windows-x64-binaries.zip` from `get.enterprisedb.com`; extracted runtime bin/lib/share directories under ignored `var/postgresql16/pgsql`. No system service, PATH change or modification to another installation.
- Cluster data is in ignored `var/postgresql16/data`, listening only on **127.0.0.1:55432**, with SCRAM password authentication. Generated bootstrap/application/test credentials are local files, never printed or committed. Windows ACLs restrict local secret storage to the current user.
- Actual SQL connections to both databases reported PostgreSQL 16.15. Clean stop/start/status succeeded. Final live checks returned **200** from API `/api/v1/health`, API `/api/v1/ready`, and frontend `/login`.

## Development/test separation and migrations

| Purpose | Database | Owner |
| --- | --- | --- |
| Development servers and persistent demos | `solarops_dev` | `solarops` |
| Destructive pytest fixtures only | `solarops_test` | `solarops_test_runner` |

Owners have different generated passwords and are not bootstrap superusers. PUBLIC CONNECT was revoked for both databases. An actual connection attempt using the test role against `solarops_dev` was **denied by PostgreSQL**. Credentials are omitted from this report.

The root ignored `.env` contains separate application and test URLs. Pytest reads the test URL, validates that its database name is exactly `solarops_test`, and sets its own process environment to test mode. Immediately before dropping the test schema it rechecks the name. Schema grants now use CURRENT_USER rather than assuming the development role. `solarops_dev` is an explicit negative guard case. Development seeds and reset commands require local `solarops_dev` plus development mode; all three commands were exercised with test-mode/test-database settings and rejected them before writes.

Alembic upgrade on development succeeded. PostgreSQL tests repeatedly migrated the test database from an empty public schema. Both databases reached head **68d7cd857e38**, with **13 public tables**, **27 indexes**, foreign keys, unique constraints and check constraints. Application status/grid enums are represented by constrained strings, not native PostgreSQL enum types. No `metadata.create_all()` shortcut was used.

The verifier recorded a development fingerprint of user identities/roles, enquiry identifiers/statuses/ownership/sites and history. It remained unchanged after PostgreSQL restart and repeated pytest schema resets. Snapshot counts were **16 users, 8 enquiries and 14 history rows**, including demo seed data and records intentionally created by browser runs. The preservation proof does not claim that every possible column or table was fingerprinted.

## Seed data and normal login

`scripts/seed_dev.py` creates the six original staff accounts used by the existing E2E scenario. New `scripts/seed_demo.py` creates five demo accounts (three customers, sales and admin) using validated account factories, Argon2id hashes, active/preverified flags and audit events. Enquiries and qualification changes use the existing domain services, preserving history, reference allocation, idempotency and audit rules.

| Demo persona | Login identifier |
| --- | --- |
| Residential customer | `customer.demo@solarops.example.com` |
| Commercial customer | `commercial.demo@solarops.example.com` |
| Industrial customer | `industrial.demo@solarops.example.com` |
| Sales | `EMP-SALES-DEMO-001` |
| Admin | `EMP-ADMIN-DEMO-001` |

Requested `.test` addresses are rejected by the actual Pydantic email validator as reserved domains; example.com subdomains were used. Employee IDs were adapted to the supported `EMP-` prefix. The database has no customer-type classification column; these are distinct scenario profiles, not invented model fields.

Generated demo passwords are stored in **`var/demo-credentials.json`** under the checkout root. The legacy staff password is in `var/dev-seed-password.txt`. Retrieve them locally using the editor or clipboard instructions in [LOCAL_POSTGRESQL.md](LOCAL_POSTGRESQL.md); do not print or paste them into reports. Both files are gitignored. No password is included here.

Four stable seed enquiries cover Chennai residential (submitted and not qualified, with a structural-reinforcement reason), Hyderabad commercial (under review), and Bengaluru industrial pilot rooftop (qualified). All use supported capacities of 2000–5000 watts, integer-paise electricity bills, valid PIN codes and grid preferences. The industrial example respects the current 5 kW maximum rather than inventing an unsupported industrial capacity. Final SQL confirmed exactly one seed enquiry in each supported status. Re-running both seeds created **zero new accounts/enquiries**. No quotation, order, stock or payment records were fabricated.

## Executed test results

| Check | Final evidence |
| --- | --- |
| Original blocked PostgreSQL cases | **31 passed**, 7.83s on first successful database run |
| Expanded runtime category | **21 passed**, 35 deselected, 2.57s |
| Expanded PostgreSQL category | **35 passed**, 21 deselected, 11.96s |
| Final complete backend suite | **56 passed**, 0 failed/skipped/blocked, 11.16s |
| Auth module diagnostic rerun | **11 passed**, 2.16s; individual affected test also passed |
| Frontend Vitest | **7 passed**, 2 files, 712ms |
| Complete Chromium suite | **4 passed**, 0 failed/skipped, 44.1s |
| TypeScript and ESLint | PASS |
| Next.js production build | PASS, 26 pages; build includes type/lint checks |
| Ruff lint and formatting | PASS, 47 Python files formatted |
| Python compileall | PASS for app/tests/scripts |
| Live OpenAPI vs checked-in JSON | PASS |
| Regenerated TypeScript vs checked-in schema | PASS |
| Schema heads/constraints and database isolation | PASS |
| Development fingerprint preservation across test reset | PASS |
| Seed/reset commands reject test target | PASS |

Backend runs emit an existing Starlette/HTTPX TestClient deprecation warning. Next lint also reports its existing deprecation notice. Neither was suppressed.

### Browser behavior actually exercised

1. Existing signup → development mailbox OTP → email verification → login → customer enquiry → reload → original sales employee review → status update → customer view.
2. Seeded customer normal login → dashboard → create enquiry with HTTP201 → authenticated persisted GET200 → reload. Anonymous enquiry read returns 401; logout without CSRF returns 403; customer sales-only PATCH returns 403.
3. Separate seeded sales browser context signs in, sees the created reference, qualifies it with HTTP200 and a note. Customer signs out (subsequent `/auth/me` returns 401), signs back in, views the qualified enquiry, refreshes and sees persisted submitted→qualified history with sales actor.
4. Seeded admin signs in through the ordinary employee flow and sees the database-backed employee list. Login rendering/portal switching smoke also passes without page errors.

These flows exercised the Next same-origin proxy, cookie forwarding, CSRF and FastAPI against real PostgreSQL. They did not mock successful persistence or disable any security dependency.

## Failures, root causes and corrections

| ID | Evidence / cause | Correction / status |
| --- | --- | --- |
| INFRA-001 | No reachable PostgreSQL at the previous default endpoint; initial QA had 31 setup errors. | Isolated portable local cluster, separate databases/roles, generated configuration; all original 31 now executed and passed. |
| QA-DB-001 | Fixture assumed schema grants to hard-coded `solarops`, while isolated tests use their own owner. | Grant to CURRENT_USER; actual clean migration and all DB tests passed. |
| QA-VERIFY-001 | Local verification script initially expected `InsufficientPrivilege`; psycopg reports startup database CONNECT denial as OperationalError. | Recognize only the explicit database permission-denial error; both schema checks and preservation comparison passed after correction. Other connection failures still propagate. |
| QA-E2E-001 | Original browser trace showed signup201 but no mailbox request after early click. Waiting only for server-rendered heading did not establish full document readiness. Later trace showed mailbox200/verify200 but no login request after the next redirect. | Wait for document load on both redirected pages and mailbox-loaded confirmation before verification. No sleeps or OTP bypass. Original flow passed in complete regression. |
| QA-E2E-002 | Original `getByLabel("City")` matched City, capacity and electricity labels; broad status text also included history. | Exact field/status locators preserve intended assertions. Complete regression passed. |
| QA-E2E-003 | New seeded test got HTTP201 but Chromium could not read its response body after full navigation. | Wait for detail URL and independently GET persisted enquiry via authenticated proxy. Full seeded workflow passed. |
| QA-FLAKE-001 (open, medium) | One later full backend run produced 55 passes/1 failure: correct captured OTP was rejected during `test_missing_csrf_rejected` setup with HTTP400 `invalid_verification_code`. Prior full run passed 56; isolated rerun passed; auth module passed; final full run passed 56. Clock difference measured 0.026s. | Root cause unestablished. Added failure-only boolean diagnostics (challenge present/expired/consumed/code matches), never secret values. Did not change authentication or weaken assertions. Keep investigating if it recurs. |

Two guard statements initially failed the formatter after editing; Ruff formatting corrected them and the final check passed. Initial browser failures were real failed executions, not counted as final passes. No production request-handling, OTP, CSRF, hashing, rate-limit or RBAC implementation was modified.

## Commands and reproduction

Full action history, including failed attempts, is in `QA_ACTION_LOG.txt`. Installation and credential-safe startup details are in [LOCAL_POSTGRESQL.md](LOCAL_POSTGRESQL.md). Download used:

```powershell
curl.exe --fail --location --retry 2 --output var/postgresql16/postgresql.zip https://get.enterprisedb.com/postgresql/postgresql-16.15-1-windows-x64-binaries.zip
```

Archive bin/lib/share members were extracted with Python zipfile under ignored `var/postgresql16`. From `apps/api`, executed commands included:

```powershell
uv run python scripts/local_postgres.py init
uv run alembic upgrade head
uv run python scripts/seed_dev.py
uv run python scripts/seed_demo.py
uv run python scripts/seed_demo.py
uv run python scripts/check_local_db.py record
uv run python scripts/local_postgres.py stop
uv run python scripts/local_postgres.py start
uv run python scripts/local_postgres.py status
uv run pytest -m 'not database' -vv
uv run pytest -m database -vv
uv run pytest -vv
uv run python scripts/check_local_db.py verify
uv run pytest tests/test_auth.py::test_missing_csrf_rejected -vv --tb=short
uv run pytest tests/test_auth.py -vv --tb=short
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run python -m compileall -q app tests scripts
uv run python scripts/export_openapi.py
git diff --exit-code -- ../../contracts/generated/openapi.json
```

Helper/migration/lint/export commands also used the equivalent synced `.venv\Scripts\python.exe` / `ruff.exe` directly; exact marker/full test commands used `uv run`. Both execute the same locked environment. The final full retry used `uv run pytest -vv --tb=short`. Development preservation was rechecked after it.

From `apps/web`:

```powershell
npm test
$env:SOLAROPS_SEED_PASSWORD=(Get-Content -LiteralPath ../../var/dev-seed-password.txt -Raw).Trim()
$env:NEXT_TELEMETRY_DISABLED='1'
npm run e2e -- --workers=1
npm run typecheck
npm run lint
npm run build
npm run generate:api
git diff --exit-code -- src/generated/schema.ts
```

Affected browser modules were also run separately while debugging. Regenerated contract files were content-identical and restored to avoid line-ending/stat noise. All secret/data/browser artifacts remain ignored. QA left development API/frontend running in hidden local processes; metadata is in ignored `var/demo-processes.json`, logs in `var/api.*.log` and `var/web.*.log`. PostgreSQL is also left running. The app is available at `http://127.0.0.1:3000/login`.

## Files changed

- Configuration/docs: `.env.example`, `docker-compose.yml`, `README.md`, `docs/qa/LOCAL_POSTGRESQL.md`, this report; historical baseline/explanation docs now point to this verification.
- Local infrastructure/seeds: `apps/api/scripts/local_postgres.py`, `local_secrets.py`, `check_local_db.py`, `seed_demo.py`; updated existing `seed_dev.py` and `reset_dev_db.py` development guards.
- Tests: `apps/api/tests/conftest.py`, `test_runtime.py`, `test_database.py`; `apps/web/e2e/enquiry.spec.ts`, new `seeded.spec.ts`.
- Audit trail: `QA_ACTION_LOG.txt`. No local credentials, environment, databases, mailbox or generated traces are committed.

## Remaining limitations and acceptance

All requested local infrastructure/workflow acceptance checks passed in their final executions. The intermittent OTP failure remains an open reliability finding. Horizontal rate limiting, concurrent enquiry/qualification races, production SMTP, Linux CI, Python 3.12 and Node 22 were not newly verified; future business modules remain unimplemented. Remote CI was not triggered and no GitHub push was attempted.

| Acceptance criterion | Status |
| --- | --- |
| Local PostgreSQL working | PASS |
| Separate development/test databases and privilege boundary | PASS |
| Alembic on both databases | PASS |
| All 31 previously blocked cases actually executed | PASS |
| Active/preverified demo users authenticate normally | PASS |
| Realistic persistent development enquiries | PASS |
| Customer→sales→customer PostgreSQL workflow | PASS |
| Complete browser tests executed | PASS |
| Final applicable local quality/contract checks | PASS |
| Development demo records survive test schema reset | PASS |
| QA branch only; no secrets committed | PASS |
| Intermittent OTP reliability investigation | OPEN |
| Push | NOT ATTEMPTED — explicit user approval required |

Final local commit SHA and working-tree status are reported in chat after review/commit.
