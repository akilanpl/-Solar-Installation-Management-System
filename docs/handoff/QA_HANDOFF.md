# QA handoff

Work on `test/qa-integration`. API tests live in `apps/api/tests`. Browser tests live in `apps/web/e2e`.

## What the automated tests cover

`uv run pytest` uses PostgreSQL. It signs up a customer, reads the OTP from the in-memory test email sender (not from a log line), and checks the challenge table stores a hash. It also creates a separate sales user and checks qualification, history, and the customer's view of the new status.

The test database is wiped with `DROP SCHEMA` at session start and truncated between tests. The guard is the database name `solarops_test`.

Frontend unit tests cover role routing and paise formatting. They do not claim the browser flow passed.

## Browser test

`apps/web/e2e/enquiry.spec.ts` signs up, loads the development mailbox code, submits an enquiry, reloads, signs in as `EMP-SALES-001`, and checks the customer sees the new status.

```sh
cd apps/web
SOLAROPS_SEED_PASSWORD="$(tr -d '\n' < ../../var/dev-seed-password.txt)" npm run e2e
```

Playwright starts uvicorn and `next dev`. The API must be in `development` so the mailbox route exists, which is the default `.env`. If Chromium cannot launch, say so. Do not mark the test passed.

## Still to add

- Survey, quotation, stock, and payment tests when those routes exist.
- A test that two concurrent enquiry creates get different reference numbers.
- CI browser job once the local browser run is stable. The current workflow runs pytest, lint, typecheck, build, and OpenAPI diff. It does not yet run Playwright.

## Do not

- Point pytest or `reset_dev_db.py` at a database whose name is not the one the script allows.
- Seed demo enquiries to make the dashboard look busy.
