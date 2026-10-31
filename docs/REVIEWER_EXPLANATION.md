# How Phase 1 works

This note is for a reviewer who wants to see the mechanism, not a diagram of a finished product. File names below are the ones in this repository.

## 1. Why FastAPI

The routes in `apps/api/app/api/v1` declare a Pydantic request model and a response model. FastAPI turns those into OpenAPI. `scripts/export_openapi.py` calls `app.openapi()` and writes `contracts/generated/openapi.json`. A route that is not in that file is not a working endpoint. Planned work stays in `docs/api/API_CONTRACTS.md` so the generated client cannot call it by mistake.

## 2. Why PostgreSQL

Enquiries have owners, sites, and a status history. Those are foreign keys. The capacity and bill checks are `CHECK` constraints in the Alembic revision, so a bug that skipped Pydantic would still fail the insert. Uniqueness of email, employee id, enquiry reference, and the idempotency pair is also in the database.

## 3. What SQLAlchemy does

`app/models` describes the tables. `app/repositories/queries.py` builds `select()` statements. SQLAlchemy sends those as parameterized SQL. The services do not assemble SQL by concatenating user input. `get_db` in `app/db/session.py` is the session for one request.

We use a synchronous session on purpose. Migrations, tests, and handlers all block on the database in the same way. The installation volume in the brief does not justify a second, async, driver.

## 4. What Alembic does

`alembic upgrade` runs `68d7cd857e38_phase_1_identity_enquiry_catalogue.py` against an empty database. That file creates tables and inserts roles and catalogue rows. The application never calls `create_all`. pytest proves this by dropping `public` on `solarops_test` and upgrading before the tests.

## 5. How an enquiry moves

The form in `apps/web/src/app/customer/enquiries/new/page.tsx` converts the bill to paise with `rupeesToPaise` and posts JSON to `/api/v1/enquiries` with an `Idempotency-Key`. The Next.js proxy forwards it. `create_enquiry` in `app/services/enquiry_service.py` checks the session user is a customer, hashes the body, inserts the site and enquiry, allocates `ENQ-YYYY-######` from `enquiry_counters`, and adds a history row and an audit event. `get_db` commits. A refresh calls `GET /api/v1/enquiries/{id}` and reads that row back.

Sales opens the same id. `qualify_enquiry` checks the role and `QUALIFICATION_TRANSITIONS`, updates the status, and appends history and audit in that same transaction. The customer page reads the new status from the API.

## 6. How Pydantic validates

`EnquiryCreate` in `app/schemas/__init__.py` rejects extra fields, a phone that is not a 10-digit Indian mobile, a PIN that is not 6 digits, a capacity outside 1–5 kW, and a negative bill. FastAPI returns 422 `validation_error` with field messages. The React form repeats some of these checks so the user sees them immediately. The database checks remain the last line.

## 7. How relational integrity is maintained

`enquiries.customer_user_id` references `customer_profiles`, so a staff user id cannot be stored as the owner. `enquiries.site_id` references `customer_sites`. History references both the enquiry and the actor user. Deleting those rows is not a feature; the foreign keys would block an accidental delete.

## 8. How commit and rollback work

If `qualify_enquiry` raises `invalid_transition`, the exception leaves `get_db`, which calls `session.rollback()`. The status and the history row are not kept. The failed OTP path is the exception: `verify_email` commits the attempt counter before raising, otherwise a rollback would erase the failed guess. That is commented in the function.

## 9. How login sessions work

`authenticate` verifies the Argon2id hash, rejects unverified and inactive users, and stores the HMAC of a new random token. The cookie `solarops_session` is HTTP-only. `GET /api/v1/auth/me` hashes the cookie again and loads the user. Logout sets `revoked_at`. A copied cookie after logout fails the revoked check.

## 10. Why the Admin menu does not grant admin

The login page dropdown is React state named `portal`. The JSON body sends `account_kind` of `customer` or `employee` only. It does not send the dropdown value as a role. The server also accepts an optional `intended_role` and throws it away in `login()` (`_ignored_client_role_hint`). The role on the response is `users.role_code`. `destinationAfterLogin` in `apps/web/src/lib/access.ts` sends a customer to `/customer` even if they asked for `/admin`. The page gate and the API both check the role again.

## 11. How the TypeScript types stay aligned

`npm run generate:api` runs `openapi-typescript` on the exported OpenAPI file. `src/lib/api.ts` imports `components["schemas"]`. CI diffs the OpenAPI file and the generated schema so a route change without a regenerated client fails the build.

## 12. How three developers work

The frontend branch consumes the generated client and does not invent rows. The backend branch adds tables through Alembic and routes through FastAPI, then regenerates the contract. QA adds pytest or Playwright against those routes. `CONTRIBUTING.md` lists the branch names and the commands.

## 13. How tests prove behavior

`tests/test_enquiries.py` inserts through HTTP and then queries `enquiries` and `enquiry_status_history` with SQLAlchemy. A second customer receives 404 for the first customer's id. The sales user is a different row with role `sales`. The OTP test reads `code_hash` and asserts the plaintext code is not that column. None of these tests replace the database with a dict of expected JSON.

## 14. How later modules fit

SysCache, assignment, StockSense-style stock, and weather are specified in `docs/architecture/INTEGRATION_BOUNDARIES.md`. The code boundary is `registered_providers()`, which is empty. Catalogue packages are real rows because the company sells those products. They have no price and no stock count. The enquiry workflow does not pretend to be a quotation.
