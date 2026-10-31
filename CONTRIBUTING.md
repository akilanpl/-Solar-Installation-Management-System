# Contributing

Three people can work at the same time because the HTTP contract and the database migration are shared, and the UI does not invent data the API does not return.

## Branches

| Branch | Owner |
| --- | --- |
| `main` | Integrated Phase 1 baseline |
| `phase-1/foundation` | This foundation, until it is merged |
| `feature/frontend-workspaces` | Frontend developer |
| `feature/backend-workflows` | Backend developer |
| `test/qa-integration` | QA developer |

Create the feature branch from the current foundation commit. Do not put everyone's new work on one shared branch.

```text
feature/<area>-<short-topic>
fix/<area>-<short-topic>
```

## Commits

Write the subject in the imperative, and say why the change exists.

```text
Record enquiry qualification in the same transaction as the status change

Sales updates were visible before the history row existed when the request failed halfway.
```

Do not commit `.env`, `var/`, mailbox files, or seed passwords.

## Pull requests

Use the pull request template. A reviewer needs:

- What behavior changed.
- Which roles can call it.
- Whether a migration or OpenAPI file changed.
- The commands you ran and their results.

## Contract changes

1. Change the FastAPI route or Pydantic model.
2. Run `uv run python scripts/export_openapi.py` from `apps/api`.
3. Run `npm run generate:api` from `apps/web`.
4. Commit `contracts/generated/openapi.json` and `apps/web/src/generated/schema.ts` together.

Planned endpoints stay in `docs/api/API_CONTRACTS.md`. Do not add them to FastAPI until they persist real data and enforce their rules.

Schema changes go through Alembic. Do not call `Base.metadata.create_all` at startup.

## Conflicts

If two branches change a migration, do not edit the merged revision in place. Add a new revision. If both branches changed OpenAPI, regenerate it from the merged FastAPI app instead of hand-merging JSON.

## Definition of done

- Backend validation rejects bad input even if the UI is bypassed.
- Authorization is checked in FastAPI.
- The change has a pytest, a typecheck, or a browser test that fails if the behavior regresses.
- Empty states stay empty. No sample revenue, stock, or jobs.
- `uv run pytest`, `npm test`, `npm run typecheck`, and `npm run lint` pass.

## Required commands before review

```sh
cd apps/api && uv run ruff check app tests scripts && uv run pytest
cd apps/web && npm test && npm run typecheck && npm run lint
```
