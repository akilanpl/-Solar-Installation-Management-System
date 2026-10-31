# SolarOps

SolarOps is the operations system for SunPower Solutions, a rooftop solar installer. Phase 1 is the foundation: a real PostgreSQL database, authenticated accounts, and one working workflow from a customer enquiry to a sales qualification update.

Later phases add surveys, quotations, warehouse movement, installation evidence, support, and reporting. Those are specified in `docs/api/API_CONTRACTS.md`. They are not implemented here, and the interface does not invent their numbers.

## What runs locally

| Piece | Role |
| --- | --- |
| Next.js app on port 3000 | Browser UI and same-origin `/api` proxy |
| FastAPI on port 8000 | Validation, authorization, transactions |
| PostgreSQL | Source of truth |

The browser talks only to Next.js. Next.js forwards `/api/v1/*` to FastAPI and passes session cookies through. See `apps/web/src/app/api/[...path]/route.ts`.

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js 22 or newer
- PostgreSQL 15 or 16

Docker is optional. `docker-compose.yml` starts PostgreSQL 16. This machine was verified with Homebrew PostgreSQL 15.19 because Docker was not installed. Do not start Compose on port 5432 while a local PostgreSQL server is already using it.

### Local PostgreSQL without Docker

```sql
CREATE ROLE solarops LOGIN PASSWORD 'solarops';
CREATE DATABASE solarops_dev OWNER solarops;
CREATE DATABASE solarops_test OWNER solarops;
```

The password above is a local development password published in `.env.example`. It is not a production secret. Keep `solarops_dev` and `solarops_test` separate: pytest drops the test database's public schema. For the isolated Windows cluster with generated credentials, follow [local PostgreSQL setup](docs/qa/LOCAL_POSTGRESQL.md).

## Start the stack

```sh
cp .env.example .env
# Put a random SOLAROPS_SECRET_KEY of at least 32 characters in .env.

cd apps/api
uv sync
uv run alembic upgrade head
uv run python scripts/seed_dev.py
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd apps/web
npm ci
npm run dev
```

Open http://127.0.0.1:3000.

The web app reads `apps/web/.env.development` for `NEXT_PUBLIC_SOLAROPS_ENV`. That flag only shows the local mailbox button. The API still refuses the mailbox route outside development.

`make seed` writes a staff password to `var/dev-seed-password.txt` when `SOLAROPS_SEED_PASSWORD` is unset. That file is gitignored. Staff sign in with an employee ID such as `EMP-SALES-001`.

Customer registration sends a 6-digit code. In development, with no `SOLAROPS_SMTP_HOST`, the API appends the message to `var/dev-mailbox.jsonl`. The verify screen can load that code. Production does not mount a successful mailbox response: `GET /api/v1/dev/mailbox/{email}` returns 404 unless `SOLAROPS_APP_ENV=development` and SMTP is unset.

## Tests

```sh
cd apps/api && uv run pytest
cd apps/web && npm test && npm run typecheck && npm run lint && npm run build
```

API tests drop and migrate only a database named `solarops_test`. They refuse any other name.

Reset the development database:

```sh
cd apps/api && uv run python scripts/reset_dev_db.py --yes
```

That command refuses to run unless the environment is `development` and the database name is exactly `solarops_dev`. It deletes development data; it is not part of normal startup.

Browser test, after the staff password exists:

```sh
cd apps/web
SOLAROPS_SEED_PASSWORD="$(tr -d '\n' < ../../var/dev-seed-password.txt)" npm run e2e
```

The seeded-account browser scenarios also require `uv run python scripts/seed_demo.py` from `apps/api`. It creates verified local demo accounts and realistic enquiries in `solarops_dev`; generated passwords remain in ignored `var/demo-credentials.json`.

## Layout

```text
apps/api        FastAPI, SQLAlchemy, Alembic, pytest
apps/web        Next.js workspaces
contracts/      Live OpenAPI plus a pointer to planned contracts
docs/           Architecture, security, handoff, reviewer notes
```

Branch and review rules are in `CONTRIBUTING.md`.
