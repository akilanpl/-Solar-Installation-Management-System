# How the SolarOps baseline tests work

All paths below are relative to the repository root. See PHASE1_BASELINE_REPORT.md for the initial results and PHASE1_POSTGRESQL_INTEGRATION_REPORT.md for the subsequent PostgreSQL-backed verification.

## Test categories and the code they exercise

| Category | Tests | Implementation and purpose |
| --- | --- | --- |
| Startup, configuration, docs | `apps/api/tests/test_runtime.py` | `app/main.py:create_app`, `app/core/config.py:Settings`, `api/v1/health.py`; prove the process and contract work independently of PostgreSQL, and missing configuration is rejected. |
| Authentication | `tests/test_auth.py` | `api/v1/auth.py`, `services/auth_service.py`, `core/security.py`; protect account verification, password checks, session creation and logout. |
| Authorization | `tests/test_enquiries.py`, `tests/test_runtime.py` | `api/deps.py:current_user`, `auth_service.assert_roles`, `enquiry_service.get_visible_enquiry`; protect customer records and staff mutations. |
| Enquiry workflow | `tests/test_enquiries.py` | `api/v1/enquiries.py`, `services/enquiry_service.py`, `repositories/queries.py`, `services/presenters.py`; verify persistence, retries, sales updates, history and customer tracking. |
| Database | `tests/test_database.py`, `tests/test_health.py` | Alembic revision `68d7cd857e38`, `models/identity.py`, `models/enquiry.py`, `db/session.py`; exercise real PostgreSQL constraints, schema creation and rollback. |
| API/security boundary | `tests/test_runtime.py`, `tests/test_database.py` | Pydantic schemas, global CSRF dependency, exception handlers, cookie sessions and login/OTP rate limits. A safe response must not reveal private exception text. |
| Frontend | `apps/web/src/lib/*.test.ts`, `e2e/smoke.spec.ts`, `e2e/enquiry.spec.ts` | Role destinations, money formatting, actual browser rendering, and the full workflow when a development database and staff account exist. |

Backend implementation paths in this table are under `apps/api/app`; backend test paths are under `apps/api`.

## A complete customer-to-sales flow

1. `tests/conftest.py:signup_and_verify` obtains `/api/v1/auth/csrf`. The client keeps the CSRF cookie and sends its matching header on mutations. `api/v1/router.py` attaches `require_csrf` to the implemented API routes. It checks both matching tokens and any supplied Origin.
2. Signup reaches `api/v1/auth.py:signup`. FastAPI parses JSON into `schemas/SignupRequest`. Pydantic validates email, phone and password, normalizes names/email, and forbids extra fields such as `role`. `services/auth_service.py:signup` chooses the customer role on the server, hashes the password with Argon2id, creates the profile and a hashed OTP challenge, and records an audit event.
3. The test reads the OTP from `application.state.email_sender.messages`, an in-memory test adapter. It does not depend on SMTP. `verify_email` checks the HMAC digest, expiry and consumed state. Incorrect attempts explicitly commit their attempt counter before raising, so rollback of the rejected request does not erase the counter.
4. Login calls `auth_service.authenticate`. Customer email and employee ID use different lookups. The stored `users.role_code` determines authorization; `intended_role` is ignored. A raw random token is set in an HTTP-only cookie, while PostgreSQL stores only its HMAC digest and expiry.
5. `test_valid_enquiry_persists` logs in, obtains the current CSRF token and sends `ENQUIRY` with an `Idempotency-Key`. FastAPI resolves `current_user` from the cookie and validates `EnquiryCreate`, including nested `SiteInput`, capacity in watts, money in integer paise, grid enum and PIN code. Invalid requests cannot rely on browser validation to bypass these rules.
6. `enquiry_service.create_enquiry` permits only a customer with a profile. It hashes the normalized payload and checks the key within that customer's scope. The same key and body replay the saved result; the same key with different data returns 409. A new submission adds a site, allocates a reference through PostgreSQL `INSERT ... ON CONFLICT ... RETURNING` on the yearly counter, inserts the enquiry and initial status history, and adds the audit event.
7. SQLAlchemy `flush()` sends statements inside the open request transaction. It is not a commit. `db/session.py:get_db` commits after successful request handling, rolls back on exceptions, and closes the session. PostgreSQL enforces UUID foreign keys, unique references/idempotency keys, and check constraints. The test opens a separate SQLAlchemy session to verify committed enquiry, history and audit rows; this is not a mocked persistence response.
8. `test_sales_can_read_and_qualify_and_invalid_transition_fails` creates a separate sales user in PostgreSQL and logs in with an employee ID. Sales/admin may view all enquiries under the current policy; no assignment filter exists. Customers see only their own records. Other staff roles are denied.
9. Sales PATCHes `/api/v1/enquiries/{id}/qualification`. `qualify_enquiry` checks the database role and `QUALIFICATION_TRANSITIONS`, requires an explanation for `not_qualified`, changes the status, and adds history plus audit in the same transaction. Repeating a status returns 409.
10. The test logs sales out, logs the customer back in, and GETs the enquiry. It checks the new status and history, then independently checks the saved rows. `repositories/queries.py:get_enquiry` eagerly loads the site and history actors; `services/presenters.py` produces the response models without password/OTP/session secrets.

The browser counterpart in `apps/web/e2e/enquiry.spec.ts` also reloads the detail page. Browser requests use `src/lib/api.ts`, which adds CSRF and credentials, and `src/app/api/[...path]/route.ts`, which forwards same-origin API calls to FastAPI. Its development mailbox and seeded sales account are prerequisites; a successful Next build alone does not verify this flow.

## Why the new database tests matter

`test_constraint_failure_rolls_back_without_damaging_saved_enquiry` first creates a real enquiry through HTTP, then deliberately attempts an invalid SQLAlchemy update. PostgreSQL must raise `IntegrityError`. After `rollback()`, the original committed values and history must remain, and an HTTP read must still work. This covers negative bills, unsupported capacity, invalid status and a nonexistent site foreign key.

`test_logout_revokes_captured_cookie_not_just_browser_cookie` restores the exact pre-logout cookie after logout and expects 401. Checking only an emptied browser cookie would miss a server that failed to revoke the session.

`test_auth_endpoint_rate_limits` temporarily lowers an isolated setting with `monkeypatch`, resets the per-test limiter through the fixture, and sends two real endpoint requests. The second must return 429. It never changes shared deployment settings or depends on sleeping.

## Running and debugging

Run `uv run pytest -m "not database"` for independent runtime checks. Run `uv run pytest -m database` only with an explicitly disposable local database named `solarops_test`. The fixture drops its public schema once and migrates it, then truncates mutable tables between marked tests. New tests that need database isolation must use `pytest.mark.database`. CI runs both categories by default; unavailable PostgreSQL remains an error rather than a silently skipped success.

For a failure, use `uv run pytest tests/test_enquiries.py::test_valid_enquiry_persists -x -vv --tb=short`. A fixture `OperationalError` before the test body means connectivity/schema setup must be fixed first. A 422 points to `schemas/__init__.py` and its field details; 401 to the session lookup; 403 to CSRF/role checks; 409 to constraints, idempotency or state transitions. Check the asserted response body before changing an expectation. Query only the disposable database to distinguish an uncommitted write from a presenter issue. Re-run the affected test, then its related module, and keep the assertions that protect intended behavior.
