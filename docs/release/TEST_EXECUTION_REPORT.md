# Test Execution Report

Current completion audit, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`, integrated base `2f6e7122494ce214036d9baf98128411bdbea3c5`. Final commit/build identity and post-commit smoke are recorded in the delivered `FINAL_EXECUTION_MANIFEST.json`. Historical reports describe earlier candidates and are not current evidence.

Current execution is against the integrated base plus only the listed launcher/demo/test changes. Final source SHA, exact artifact hashes and post-commit checks are in delivered `FINAL_EXECUTION_MANIFEST.json`.

| Command / scope | Current observed outcome |
|---|---|
|`uv sync --group dev` with writable UV cache|PASS, locked Python 3.12 environment|
|`npm ci --cache /private/tmp/solarops-npm-cache --no-audit --no-fund`|PASS, 425 packages|
|`python -m alembic upgrade head`|PASS, fresh isolated demo DB, head 6a1b2c3d4e50|
|`pytest --ignore=tests/release_campaigns --junitxml=...`|508 PASS in 299.62 s; one Starlette TestClient deprecation warning|
|`pytest tests/test_complete_launcher.py`|4 PASS after correcting macOS-unsupported test socket inspection to an actual connect/accept oracle|
|`pytest tests/release_campaigns --junitxml=...`|89 PASS in 353.00 s, including five-minute real HTTP campaign and disposable backup/restore; original combined run incomplete|
|`ruff check app tests scripts`|PASS|
|`npm test`|85 PASS / 17 files|
|`npm run typecheck`|PASS|
|`npm run lint`|PASS|
|`npm run build`|PASS, production build with explicit development preview flag|
|`python scripts/export_openapi.py` + diff|PASS, no generated schema drift|
|`npm run generate:api` + diff|PASS, no generated TypeScript drift|
|Playwright smoke via complete config|BLOCKED before test interaction by macOS browser process bootstrap permissions|
|Manual supported browser|Signup through accepted quotation PASS; provider/downstream blocked; 216 viewport observations, partial acceptance|
|Logical backup restore|PASS, all 100 table row hashes match|
|Seven-role HTTP demo and launcher restart|Final results in execution manifest|

Initial pytest invocation refused the database because the disposable-name environment variable had not been exported; dotenv loading alone does not export it. All later runs explicitly passed both variables from the private `.env`. The original combined diagnostic run collected 597 tests, passed the five-minute load test, failed backup on missing CREATEDB, then hit its 600-second wrapper timeout around 79%; it is not reported as a green full suite. Release campaigns repeat selected existing tests, so their count is not newly authored distinct coverage. No baseline assertions were weakened.
