# System architecture

SolarOps Phase 1 is one Next.js app, one FastAPI process, and one PostgreSQL database. There is no Redis, queue, or second service.

## Request path

1. The browser calls `http://127.0.0.1:3000/api/v1/...` with cookies.
2. `apps/web/src/app/api/[...path]/route.ts` forwards the request to FastAPI and copies `Set-Cookie` back.
3. `require_csrf` in `apps/api/app/api/deps.py` rejects unsafe requests whose `X-CSRF-Token` header does not match the `solarops_csrf` cookie, or whose `Origin` is outside `SOLAROPS_TRUSTED_ORIGINS`.
4. `get_db` in `apps/api/app/db/session.py` opens one synchronous SQLAlchemy session, commits if the handler returns, and rolls back if it raises.
5. The route calls a service. The service uses repositories for queries and adds audit rows in the same session.

Synchronous sessions were chosen because Alembic, pytest, and the request all use the same blocking style. The company volume in the brief is about 40 installations a month, so an async driver would not remove a measured bottleneck. Mixing async routes with a sync session would block the event loop, so the whole API stays synchronous.

## Why these pieces

- **FastAPI** generates the OpenAPI document from the routes and Pydantic models that actually exist. `scripts/export_openapi.py` writes that document. Planned routes are not registered, so they cannot appear to succeed.
- **PostgreSQL** enforces foreign keys, uniqueness, and the enquiry check constraints. The API is not the only protection.
- **SQLAlchemy** maps those tables and sends parameterized statements. The enquiry insert is built with the ORM, not string-concatenated SQL.
- **Alembic** is the only schema installer. `create_app` does not create tables.

## Processes

`app.main:app` is the uvicorn entrypoint. `create_app` stores the engine, session factory, email sender, and rate limiter on `app.state`. Tests build a separate app pointed at `solarops_test`.

## What is intentionally absent

Weather, payments, complaint summaries, and technician assignment have interfaces in `app/services/future_boundaries.py`. `registered_providers()` returns an empty dict. No route returns a successful weather or payment payload.
