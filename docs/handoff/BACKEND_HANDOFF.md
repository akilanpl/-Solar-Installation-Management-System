# Backend handoff

Work in `apps/api` on `feature/backend-workflows`.

## Layout

| Path | What belongs there |
| --- | --- |
| `app/api/v1` | HTTP: status codes, dependencies, response models |
| `app/schemas` | Pydantic input and output. `extra="forbid"` on writes |
| `app/services` | Rules, transitions, audit |
| `app/repositories/queries.py` | SELECT statements |
| `app/models` | Tables |
| `alembic/versions` | Schema changes |

Keep using the synchronous session in `get_db`. Do not open a second engine inside a request.

## Enquiry slice

`enquiry_service.create_enquiry` and `qualify_enquiry` are the pattern: check the role, write the business row, write history, write audit, let `get_db` commit.

Phase 2 follows that pattern in `survey_service`, `quotation_service`, `payment_service`, and `order_service`. The review notes are in `docs/architecture/PHASE2_SALES_WORKFLOW.md`. Migration `9b1336c3b2cc` adds the tables and seeds package template version 1. Do not edit the Phase 1 migration.

Customer ownership is `customer_profiles.user_id`. Do not accept a customer id from the body.

## Adding an endpoint

1. Add the route only when it reads and writes real rows.
2. Export OpenAPI and regenerate the TypeScript schema.
3. Add a pytest that uses the database, with a customer and a staff user where the rule differs.
4. Document a planned route in `docs/api/API_CONTRACTS.md` before building it if the frontend needs the shape first. Do not register a stub that returns success.

## Commands

```sh
uv sync
uv run alembic upgrade head
uv run ruff check app tests scripts
uv run pytest
```

Tests refuse to run unless the database name is `solarops_test`.
