# Phase 3 API CI follow-up

Date: 2026-10-31 (Asia/Calcutta). Branch: `test/qa-integration`. Starting commit: `772c284`.

## Observed GitHub failure

[Push run 41192267010](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41192267010) ran commit `772c284`. The web job passed. The [API job](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41192267010/job/124511276201) successfully initialized PostgreSQL, created the disposable database and reached pytest. It finished with **119 passed, 3 failed** in 34.01s. OpenAPI checking was subsequently skipped because the test step failed.

The failures were exactly the published P3-001, P3-002 and P3-003 regressions. No new infrastructure, migration or lint failure was observed. The historical `test 1 report.txt`, `test 3 report.txt` and Phase 3 QA report remain unchanged; this document records the subsequent correction.

## Minimal corrections

Only `apps/api/app/services/installation_service.py` changes product behavior:

1. `verify_customer_otp`: commit the rejected attempt counter before raising the wrong-code error, following the established Phase 1 email verification policy. Previously `flush()` was followed by the request dependency's rollback, so the counter never accumulated. The current HTTP call path has performed only reads/locks before this increment; no job state/audit writes precede the failure branch. Successful OTP processing retains its normal request transaction. Existing row locks still serialize attempts.
2. `create_job`: reject a technician whose stored `is_active` flag is false before creating job or OTP rows. Existing role/existence checks and error response remain.
3. `complete_job`: require both `on_site` state and a server-recorded arrival before completion. This gate follows the existing OTP/evidence/signature checks, retaining their error precedence and the documented installation state machine.

No regression assertions, markers, workflow steps or CI failure handling were relaxed. No test was skipped or marked xfail. No frontend feature or migration was added.

## Executed local verification

| Check | Result |
| --- | --- |
| Three formerly failing tests, unchanged | 3 passed, 4.48s |
| Independent and source Phase 3 modules | 42 passed, 40.906s JUnit |
| Complete backend suite | **122 passed**, 0 failed/errors/skipped, 95.35s |
| Ruff lint and formatter | PASS; 77 files formatted |
| Python compileall | PASS |
| Live OpenAPI export vs committed JSON | PASS; no contract change |
| Protected development fingerprint before/after | PASS |

Commands from `apps/api` included the three individual selectors in `tests/test_phase3_qa_regression.py`, then:

```powershell
uv run pytest tests/test_phase3_qa_regression.py tests/test_phase3_warehouse_installation.py -q --tb=short --junitxml=../../var/phase3-ci-related.xml
uv run ruff check app tests scripts
uv run ruff format --check app tests scripts
uv run pytest -vv --tb=short --show-capture=no --junitxml=../../var/phase3-ci-full.xml
uv run python -m compileall -q app tests scripts
uv run python scripts/export_openapi.py
git diff --exit-code -- ../../contracts/generated/openapi.json
uv run python scripts/check_local_db.py verify
```

Tests reset only `solarops_test`, which remains at `d5f1a2b3c4e5` with 44 tables/104 indexes. `solarops_dev` remains at its historical `68d7cd857e38` revision with 13 tables/27 indexes. Its protected user/enquiry/history fingerprint is unchanged and the test role is still denied CONNECT. No development migrations, seeds or resets were performed.

Local verification used Windows/Python3.14/PostgreSQL16.15. The observed failed CI used Linux/Python3.12/PostgreSQL16.15. A successful local run is not a claim that a new GitHub run has passed. Publishing requires fresh user authorization; remote CI verification is pending that push.

## Remaining limitations

P3-001–003 are corrected and their unchanged local regressions pass. P3-004 (sales UI missing required qualification inputs) remains open; browser testing was not rerun for this API-only change, and the web CI job does not execute Playwright. The historical email-OTP flake remains open and did not recur here. The existing Starlette/HTTPX deprecation warning remains.

See `QA_ACTION_LOG.txt` for the chronological actions. No credentials or local database artifacts are included in this follow-up.
