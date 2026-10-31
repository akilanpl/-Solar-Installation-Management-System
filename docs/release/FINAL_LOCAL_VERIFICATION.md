# Local working candidate

Application/test candidate `88766362fb7842b2da12be73d254d81cd627c9c8` on `fix/actual-frontend-integration`. Verification 2026-10-31. Main is not merged; Phase 4 has not started.

Repository: `/Users/akilan/Downloads/SOLOPS-integration`.
Frontend: http://127.0.0.1:3002/login
Backend: http://127.0.0.1:8002/api/v1/ready
Database: PostgreSQL 15 on 5432, named candidate `solarops_ultimate_preview_20261031`, migration f3b9c0d1e2a3. Existing solarops/solarops_test and earlier preview databases were not reset. Only the explicitly named disposable release-test database is rebuilt by pytest.

The older owned 3001/8001 preview was stopped to avoid stale frontend confusion. PostgreSQL was left running. Current Next build directory is `.next-ultimate`; backend loads ignored `var/ultimate-preview.env` without shell interpolation. This is a nonproduction integration candidate, not a fresh clone of merged main.

Start in two terminals:

```sh
cd /Users/akilan/Downloads/SOLOPS-integration/apps/api
.venv/bin/python scripts/run_candidate.py
```

```sh
cd /Users/akilan/Downloads/SOLOPS-integration/apps/web
SOLAROPS_NEXT_DIST_DIR=.next-ultimate SOLAROPS_API_ORIGIN=http://127.0.0.1:8002 node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3002
```

Ctrl+C stops each owned foreground server. Do not stop/reset the shared PostgreSQL service. If a port is occupied, inspect the listener and verify ownership instead of killing an unknown process. Before rebuilding `.next-ultimate`, stop that owned Next server and restart after the build.

Nonproduction staff use EMP-ADMIN-001, EMP-SALES-001, EMP-TECH-001, EMP-WH-001, EMP-WHM-001 and EMP-SUP-001 with the existing ignored `var/dev-seed-password.txt`; no password is copied here. Do not reseed or reset existing users just to gain access.

Demonstrated records: ENQ-2026-000002 → SUR-2026-000002 approved → QTN-2026-000001 accepted, total ₹94,872.00, verified payments zero, no sales order. Separate labelled warehouse transfer STK-2026-000002 persists MAIN=2/SITE=1 and exact test serial custody. Saved technician availability and two product policies remain labelled test-only.

To unblock provider acceptance, configure the user's Razorpay TEST credentials in the ignored 0600 file `var/ultimate-preview.env`:

```text
SOLAROPS_RAZORPAY_KEY_ID
SOLAROPS_RAZORPAY_KEY_SECRET
SOLAROPS_RAZORPAY_WEBHOOK_SECRET
```

Use an rzp_test_ account/key, not a live key. Do not paste secrets into chat or commit them. Restart only the owned backend; confirm capability enabled without exposing secrets; execute genuine sandbox checkout/reconciliation and an authenticated webhook acceptance where reachable. A missing/invalid provider result must remain blocked/unknown. No actual charge, public exposure, provider settlement, supplier action or physical event is authorized by these startup instructions.

Then resume primary browser steps 12–23 with the existing accepted quotation and distinct authorized accounts. Close remaining campaign and replacement/carrier-return gaps before any main merge. The final local smoke and listener status are recorded in the user-facing report after restart.

## Final running smoke

Fresh owned backend and optimized Next server were restarted after verification. API readiness returned HTTP 200 with database up and a request ID; frontend returned HTTP 200 with X-SolarOps-Frontend: teammate-72db4a1-phase3-candidate. Browser readback preserved the accepted quotation and truthful blocked checkout; sales/admin records and all six role workspaces were exercised. Current private backup restored all 58 tables with matching rows in 0.265 seconds. Earlier owned 3001/8001 listeners are stopped; candidate 3002/8002 remains running.
