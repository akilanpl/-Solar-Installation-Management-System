# Release gate backend coverage component

Date: 2026-10-31. Source: `integration/final-release`, parent `0bdd9536dfc6a9da224ef84849dcff21e98832eb`. CI issue: CI-006. Status: **backend measurement implemented locally; overall release gate remains incomplete**.

## Problem and change

The failing pushgate reports missing coverage campaigns without collecting any measured backend coverage. Backend test totals and the heuristic score cannot establish line or branch coverage. The branch already requires 80% line and 70% branch coverage in `.pushgate/config.yml`.

The runner now executes the existing backend suite through coverage.py with `--branch --source=app`, exports machine-readable evidence and checks line/branch percentages separately against the unchanged configured thresholds. Counts, percentages, thresholds and pass/fail states are retained under the SHA's evidence directory. This scope covers the backend application only, not frontend, mutation or changed-line coverage.

`check_backend_coverage.py` rejects absent, malformed, empty and non-branch evidence rather than awarding a pass. Threshold comparisons use unrounded percentages. Ten regression tests cover independent threshold failures, rounding, malformed data, configuration use, stale artifacts and partial JUnit from failed/timed-out commands.

The runner removes prior coverage/JUnit artifacts before the corresponding stage and retains command exit status alongside individual test results. A partially successful XML file therefore cannot hide an unsuccessful command. These changes are necessary to keep coverage/test evidence fresh and trustworthy.

Only development tooling is added to `apps/api/pyproject.toml` and `uv.lock`: coverage.py and an explicit PyYAML dependency for the existing gate configuration. PyYAML was already locked transitively. Application code, production dependencies, migrations, existing test assertions, mandatory missing campaigns, score formula and thresholds remain unchanged.

## Verification

Validated in an isolated source archive using Python 3.12.13, matching CI's Python minor version. Local platform is Windows; remote gate runs on Linux and remains pending until an approved push.

| Check | Actual result |
| --- | --- |
| Original backend suite under branch measurement | 147 passed, one existing Starlette/httpx deprecation warning, 143.87 seconds |
| Backend statement coverage | 3657/4137 = 88.397%; PASS against 80% |
| Backend branch coverage | 567/920 = 61.630%; FAIL against 70% |
| Coverage checker on actual measured evidence | Exit 1, correctly rejects branch shortfall |
| Gate regression suite | 10 passed |
| API lint; new gate checker/tests lint; gate syntax | Passed |
| Frozen Python dependency sync | Passed |
| Lock drift and API contract | All pre-existing locked package records unchanged; only coverage added. Regenerated OpenAPI unchanged |
| Disposable test migration | Release head `e6a2b3c4d5f6`, 45 public tables; original fixtures performed the guarded migration |
| Development protection | Stored accounts/enquiries/history fingerprint and historical Phase1 revision unchanged before/after disposable tests |

Representative CI commands from the repository root are executed by `.pushgate/run.py`:

```sh
# Actual backend subprocess runs from apps/api:
.venv/bin/python -m coverage run --branch --source=app --data-file=ABSOLUTE_EVIDENCE/backend.coverage -m pytest --junitxml=ABSOLUTE_EVIDENCE/backend.xml
.venv/bin/python -m coverage json --data-file=ABSOLUTE_EVIDENCE/backend.coverage -o ABSOLUTE_EVIDENCE/backend-coverage.json
# Threshold checker runs from repository root:
apps/api/.venv/bin/python .pushgate/check_backend_coverage.py --coverage ABSOLUTE_EVIDENCE/backend-coverage.json --config .pushgate/config.yml --output ABSOLUTE_EVIDENCE/backend-coverage-check.json
apps/api/.venv/bin/python -m unittest discover -s .pushgate -p 'test_*.py'
```

`ABSOLUTE_EVIDENCE` above denotes the runner-created SHA evidence directory, not a literal command argument. Generated evidence, local harnesses, credentials, archives and environments are not committed.

## Remaining blockers and publication

This component intentionally does not make the current release gate green. Backend branch coverage is below threshold. All six original missing campaign categories and all ten mandatory notrun entries remain; a partial backend measurement cannot satisfy the complete coverage campaign. Browser lifecycle, missing business capabilities, load/recovery/accessibility, mutation/diff/frontend coverage, history secret scan and baseline/two-order verification still need implementation/evidence.

The full multi-stage gate and frontend checks were not rerun locally for this backend-tooling-only change. The existing head's successful ordinary CI remains historical evidence, not a claim about this new commit. Expected remote behavior is new coverage artifacts and an explicit branch-coverage failure, while the aggregate gate remains INCOMPLETE. No full release acceptance or remote success is claimed.

The dedicated local repair commit is based solely on the source release HEAD. Publication would update only `origin/integration/final-release` after exact commit approval. No automatic propagation to actual-frontend integration, QA or main is authorized. The final commit SHA is recorded separately in the QA tracker and push review because a commit cannot contain its own SHA.
