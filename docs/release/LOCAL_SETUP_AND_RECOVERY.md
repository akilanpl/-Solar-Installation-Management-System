# Local setup and recovery

Candidate is local-only until publication and exact final-source release acceptance. The active development clone is under work/solarops-complete. A separate clean local clone is prepared for delivery; it is not a GitHub-verified integration clone.

Prerequisites: Python3.12, uv, Node22+, npm lockfile, existing local PostgreSQL on5432. Docker is unavailable here; no second PostgreSQL instance was installed. Never point tests at a business or preview database: pytest resets its explicitly named disposable test schema.

```sh
cd <clean-checkout>
cd apps/api
uv sync --frozen
cd ../web
npm ci
npm run build
cd ../..
git config core.hooksPath .githooks
```

Create a NEW empty database with a unique eight-digit suffix, such as solarops_release_demo_61902847 (the session uses that name; do not recreate/overwrite it). Generate an ignored var/complete-preview.env with development environment, its local database URL, a fresh32+character secret, trusted origin http://127.0.0.1:3061, and a local mailbox path. No Razorpay credentials are required; checkout stays disabled. Only authorized rzp_test_ credentials may be placed in ignored local configuration.

```sh
apps/api/.venv/bin/python apps/api/scripts/complete_local.py migrate
apps/api/.venv/bin/python apps/api/scripts/complete_local.py seed
apps/api/.venv/bin/python apps/api/scripts/complete_local.py serve
```

Frontend: http://127.0.0.1:3061; backend: http://127.0.0.1:8061; health /api/v1/health; database readiness /api/v1/ready. Ctrl-C in the serve runner stops only its own child processes. The runner does not reset or drop any database. Ports must be free. Use production build/start locally if macOS file watching produces EMFILE; never delete other worktrees to cure that error.

Supported seed tooling creates synthetic staff/customer/enquiry fixtures. Staff IDs EMP-ADMIN-001,EMP-SALES-001,EMP-TECH-001,EMP-WH-001,EMP-WHM-001,EMP-SUP-001 use ignored var/dev-seed-password.txt. Demo identifiers/passwords are in ignored var/demo-credentials.json. Do not commit or share those files. Public customer signup and local mailbox verification remain supported; seed tooling does not alter production authorization.

Tests require a SEPARATE uniquely created solarops_release_test_XXXXXXXX database and both SOLAROPS_TEST_DATABASE_URL and SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME. The name must exactly match. Never run tests against the demo database. Run .pushgate/run.sh from a clean checkout; do not reuse successful evidence from an earlier SHA.

Before upgrades, pg_dump --format=custom to a protected ignored location; verify restore into another new database and compare source rows/business hashes. This session restored a100-table synthetic preview with all row counts equal. That is a local backup rehearsal, not production recovery certification. Roll back an application by selecting its preserved source; database rollback requires reviewed backup restoration, not destructive Alembic downgrade. Never replace a live database in place or delete signed/accounting rows.
