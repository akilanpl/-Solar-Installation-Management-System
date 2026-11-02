# Database Integrity Report

Current completion audit, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`, integrated base `2f6e7122494ce214036d9baf98128411bdbea3c5`. Final commit/build identity and post-commit smoke are recorded in the delivered `FINAL_EXECUTION_MANIFEST.json`. Historical reports describe earlier candidates and are not current evidence.

Fresh Alembic upgrade PASS to `6a1b2c3d4e50`, including the Phase 4 merge head. Current schema: 100 tables, 233 foreign keys, 80 unique constraints, 114 checks. Counts describe schema, not exhaustive correctness.

Owned databases: `solarops_release_demo_20261102`, `solarops_release_test_20261122`, `solarops_completion_restore_20261102`. The 20261122 suffix avoids an existing unrelated 20261102 test database; it is an isolation identifier, not the execution date. Demo/test data is separate. `.env` is ignored and mode 0600. Test fixtures explicitly check the disposable database name before resetting its schema.

A protected custom-format dump was restored into the newly created restore database. All 100 table row counts and SHA-256 row snapshots matched; readiness query succeeded. No existing database was restored over or dropped. Rerunning Alembic upgrade at head does not alter business rows; no destructive downgrade was attempted. Backup and secrets remain in ignored `var/`, excluded from delivered reports.

API/DB regressions cover idempotency, concurrent quotations/payments/reservations, rollback, serial custody, cancellation/returns, immutable finance entries, authorization and warranty rules. Consult `TEST_EXECUTION_REPORT.md` for actual current results; provider verification remains boundary-tested with controlled adapters rather than live credentials.
