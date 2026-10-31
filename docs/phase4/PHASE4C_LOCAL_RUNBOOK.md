# Isolated Phase 4C local runbook

Use only `~/Downloads/SOLOPS-phase4c` on
`feature/phase4c-finance-admin`. Base is
`26a5f129e1eeea5ad772ab4e1b8c5f8f6d43bc3d`.
Do not reset the populated preview when rerunning checks. Keep test and browser
work sequential within each database. Neither database is used by another phase.

## Environment and migration

Dependencies are locked in the inherited `uv.lock` and `package-lock.json`.
The checkpoint used Python 3.12.13, PostgreSQL 15.19, Next.js 15.5.28 and
the Codex managed in-app browser (engine/version not independently identified). Check the actual PostgreSQL version in
the test evidence before comparing versions on another machine.

From `apps/api`, install with `uv sync --frozen`. From `apps/web`, use `npm ci`.
The local role here is `akilan` with localhost peer/trust access; use your own
isolated development role and credentials elsewhere. Never put production URLs
or credentials in these commands.

The databases created by this task are `solarops_release_test_20261113` and
`solarops_4c_preview`, both on `127.0.0.1:5432`. Set the preview database timezone
to UTC before seeding. This avoids an inherited installation-summary hash
problem when connections return equivalent arrival times with different UTC
offsets. Only this task's preview database default was changed.

```sh
# Only when creating a NEW dedicated preview, not an existing populated one:
createdb -h 127.0.0.1 solarops_4c_preview
psql -h 127.0.0.1 -d postgres -c "ALTER DATABASE solarops_4c_preview SET timezone TO 'UTC';"
cd apps/api
SOLAROPS_DATABASE_URL=postgresql+psycopg://akilan@127.0.0.1:5432/solarops_4c_preview \
SOLAROPS_SECRET_KEY=phase4c-preview-local-secret-not-production \
.venv/bin/alembic upgrade head
.venv/bin/python scripts/seed_phase4c_acceptance.py
```

The seed refuses any database other than the local `solarops_4c_preview` and
refuses a nonempty preview. It creates synthetic accepted orders through
inherited HTTP workflows, genuine local delivery/installation evidence, an
accepted Phase 4B bill, explicit test policy/rate/checklist approvals and a
submitted technician timesheet. Its one-hour labour clock span is an explicitly
synthetic fixture. It never charges, transfers funds or submits to government.
It writes only a gitignored manifest under `var/phase4c`.

A server process could not be started with `initdb` inside this sandbox because
macOS denied shared-memory creation. A dedicated database on the already running
local PostgreSQL server worked. Do not touch another task's database or service.

## Verification

Create the disposable release-test database once if it is absent, then run the
following from `apps/api`. Pytest intentionally drops only that database's public
schema and recreates it through Alembic; this is safe only for this exact
disposable test target. Do not run another test process against it concurrently.

```sh
SOLAROPS_TEST_DATABASE_URL=postgresql+psycopg://akilan@127.0.0.1:5432/solarops_release_test_20261113 \
SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=solarops_release_test_20261113 \
.venv/bin/python -m coverage run --branch --source=app -m pytest
.venv/bin/python -m coverage json -o ../../var/phase4c/evidence/rerun-coverage.json
.venv/bin/ruff check app tests scripts
```

From the repository root, run the unchanged configured coverage evaluator:

```sh
apps/api/.venv/bin/python .pushgate/check_backend_coverage.py \
  --coverage var/phase4c/evidence/rerun-coverage.json \
  --config .pushgate/config.yml \
  --output var/phase4c/evidence/rerun-coverage-gate.json
```

The inherited repository-wide branch coverage shortfall remains a failing gate.
Do not change its threshold or describe this as a release PASS.

From `apps/web`:

```sh
npm test
npm run typecheck
npm run lint
SOLAROPS_API_ORIGIN=http://127.0.0.1:8143 npm run build
npx playwright test --config playwright.phase4c.config.ts
```

The Phase 4C Playwright config reserves only `3143`/`8143`, uses the production
Next.js build and refuses to reuse an unknown server. Stop only task-owned
preview processes before running it. This sandbox could not launch CLI Chromium
(`MachPortRendezvousServer` denied). The five requested scenarios were instead
executed with Codex's managed in-app browser against those actual local services.
The CLI suite is supplied for an environment that permits launching Chromium;
its launch failures are reported BLOCKED, never counted as application passes.

## Manual preview

From `apps/api`, start Uvicorn with the same local preview URL and development
secret shown above, `SOLAROPS_APP_ENV=test`, `SOLAROPS_COOKIE_SECURE=false`,
`SOLAROPS_TRUSTED_ORIGINS=http://127.0.0.1:3143`, a task-owned evidence directory,
and `--host 127.0.0.1 --port 8143`. From `apps/web`, run
`SOLAROPS_API_ORIGIN=http://127.0.0.1:8143 npx next start --hostname 127.0.0.1 --port 3143`.
The evidence directory used here is the absolute worktree path followed by
`/var/phase4c/uploads`. Never bind these test fixtures to a public interface.

Synthetic accounts use the inherited fixture credentials: admin
`EMP-ADMIN-941`, technician `EMP-TECH-901`, sales `EMP-SALES-901`, each with
`Staffpass123`; customer `leela@example.com` with `Solarops123`. These are local
test accounts only, not deployable credentials. The UI selects a sign-in form;
the persisted account role supplies actual authorization.

The populated checkpoint retains completed browser fixtures; do not rerun the
fresh-seed script over them. Database resets performed during seed diagnosis
were confined to the task-created preview. Final records, manifests, detailed
logs, coverage data and downloaded CSV remain under `var/phase4c`. No deployment,
push, merge, live provider call or real customer record was involved.
