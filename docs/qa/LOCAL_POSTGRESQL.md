# Isolated PostgreSQL and local demos (Windows)

Use the Git checkout containing this document (`qa-checkout` in this workspace). No system PostgreSQL service is installed. The portable PostgreSQL 16 cluster lives in ignored `var/postgresql16` and listens only on `127.0.0.1:55432`.

## Installation and lifecycle

The [official PostgreSQL Windows page](https://www.postgresql.org/download/windows/) links to [EDB binary archives](https://www.enterprisedb.com/download-postgresql-binaries). This setup used `https://get.enterprisedb.com/postgresql/postgresql-16.15-1-windows-x64-binaries.zip`. Download it to `var/postgresql16/postgresql.zip` and extract its `pgsql/bin`, `pgsql/lib` and `pgsql/share` folders under `var/postgresql16`. Do not replace an existing cluster or its configuration.

From `apps/api`:

```powershell
uv sync --frozen
uv run python scripts/local_postgres.py init
uv run python scripts/local_postgres.py status
uv run python scripts/local_postgres.py stop
uv run python scripts/local_postgres.py start
```

`init` generates separate SCRAM credentials, initializes only its own data directory, starts the server and creates `solarops_dev` and `solarops_test`. It writes a new root `.env` only if one does not already exist. Existing `.env` contents are preserved. It does not touch other PostgreSQL installations, register a service or change the system PATH. Re-running it preserves passwords and data. Stop uses a clean fast shutdown; start reuses the existing data directory. The cluster does not automatically start after reboot.

`var` and generated secret files are restricted to the current Windows account using ACLs. `.env`, local configuration, database data, mailbox, credentials, snapshots and server logs remain gitignored. Never copy them into a report or commit them. Do not run this cluster under another Windows account without explicitly managing its filesystem permissions.

## Database isolation

| Purpose | Database | Local owner |
| --- | --- | --- |
| Application and persistent demo data | `solarops_dev` | `solarops` |
| Destructive pytest setup only | `solarops_test` | `solarops_test_runner` |

Both are non-superuser login roles with different generated passwords. PUBLIC cannot CONNECT to either database; the test role cannot CONNECT to development. PostgreSQL bootstrap credentials are used only by the local cluster helper. Never use them as application/test credentials.

The ignored root `.env` contains separate `SOLAROPS_DATABASE_URL` and `SOLAROPS_TEST_DATABASE_URL` values. Pytest reads only the latter, validates the exact database name, and overrides application settings to test mode for its own process. Normal development servers keep using the development URL. Never export the test URL as the development URL. Before resetting, the fixture rechecks the name; it drops only `solarops_test.public`. It grants the recreated schema to the current test owner, without depending on the development role.

## Migrate and seed

From `apps/api`:

```powershell
uv run alembic upgrade head
uv run python scripts/seed_dev.py
uv run python scripts/seed_demo.py
uv run python scripts/seed_demo.py
uv run pytest -m database -vv
uv run python scripts/check_local_db.py record
uv run pytest -vv
uv run python scripts/check_local_db.py verify
```

The first migration targets development. The database test fixture migrates the disposable database from an empty schema. The snapshot verifier checks both migration heads and constraints, attempts a real test-role connection to development (which must be denied), and compares development users, enquiry statuses and history before/after pytest. Run record/verify without concurrent demo writes or browser workflows between them.

`seed_dev.py` supplies the original six staff accounts used by the existing browser workflow. `seed_demo.py` adds three customer personas, demo sales/admin accounts and four enquiries through validated domain services. All demo accounts are active and preverified. Password hashing and ordinary session login remain enforced. The seed rejects non-development mode, non-local hosts, and every database except `solarops_dev`. Repeating it reuses credentials and per-customer idempotency keys; it does not revert later qualification changes.

| Demo role | Identifier |
| --- | --- |
| Residential customer | `customer.demo@solarops.example.com` |
| Commercial customer | `commercial.demo@solarops.example.com` |
| Industrial customer | `industrial.demo@solarops.example.com` |
| Sales | `EMP-SALES-DEMO-001` |
| Admin | `EMP-ADMIN-DEMO-001` |

The requested `.test` email domain is reserved and rejected by the actual email validator, so example.com subdomains are used. Employee IDs include the schema-required `EMP-` prefix. Persona categories are seed scenarios; the current profile model has no residential/commercial/industrial type field. Capacity stays within the implemented 1–5 kW range, including an industrial pilot rooftop; money is integer paise.

Passwords are in `var/demo-credentials.json` at the checkout root. Open it locally in an editor, or copy one password to your clipboard without printing it (from checkout root):

```powershell
$demo = Get-Content -LiteralPath var/demo-credentials.json -Raw | ConvertFrom-Json
Set-Clipboard -Value $demo.'customer.demo@solarops.example.com'.password
```

Clipboard contents contain a local demo credential. Clear them after use. Never paste passwords into this chat or a report. The existing staff password is separately stored in `var/dev-seed-password.txt`.

## Run the app and browser suite

From `apps/api`, run `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`. In a second terminal under `apps/web`, run `npm run dev`, then open `http://127.0.0.1:3000`. Normal login, same-origin proxy, HTTP-only cookies and CSRF remain active.

From `apps/web`, the complete browser suite starts/stops the API and frontend automatically when they are not already running:

```powershell
npx playwright install chromium
$env:SOLAROPS_SEED_PASSWORD=(Get-Content -LiteralPath ../../var/dev-seed-password.txt -Raw).Trim()
npm run e2e -- --workers=1
```

Run this in a fresh shell with development settings; do not carry `SOLAROPS_APP_ENV=test` or test-database overrides over from earlier troubleshooting. Reused servers must point to the intended local development cluster. Browser tests add real enquiries to development and preserve them. Generated traces/results are ignored and may contain sensitive form data; do not publish them indiscriminately.
