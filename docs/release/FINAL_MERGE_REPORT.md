# Integration and merge checkpoint

Status: PARTIAL. Overall RELEASE BLOCKED.

Remote main independently verified using `git ls-remote origin refs/heads/main`: a95533838fd4413233ed69edf2ce671260ea8c3a. No push or PR was performed; no main merge occurred. The local credentials successfully fetched GitHub/CI metadata, so missing Git credentials are not asserted as the blocker.

History-preserving local merge: 831cb906a9af8644020231a6696d7fceed7257f6 includes QA c83bd1150d07e26e9fc8769cc7ea52a9a49a016e and Phase 3 ae212b2cdfce755b69ec9a73df15f3907873bf0d. Incremental remediation commits: 504166d (customer-bound verification/evidence), 2e79ad4 (owning-customer code reissue), c48df6b (authenticated quotation/jobs UI), ffae1ecf63d8d99b71f6a3d02ee6f531e275c253 (release gate). Later documentation-only checkpoint may be HEAD; see `git log` for immutable final report commit.

Gate at tested code SHA ffae1ecf63d8d99b71f6a3d02ee6f531e275c253: INCOMPLETE, computed 55.4/100 (F), no executed stage failures, required campaign gaps remain. No bypass or force push. The applied pushgate skill explicitly says “FAIL or INCOMPLETE: do not push”; the integration branch remains committed locally because this campaign is incomplete. Mandatory internal requirements are unfinished, so the mission's no-main-merge gate also applies. This is not an external-credentials-only blocker.

GitHub returned `Branch not protected` (404) for main protection at inspection. No protection was removed, changed or bypassed. New pushgate workflow has not run on GitHub because this branch is unpushed; no remote exact-head CI result or review approval exists. Historical QA/frontend CI results cannot certify this integration head.

Manual future commands, ONLY AFTER the full gate actually passes and remaining work is complete:

```sh
git fetch origin --prune
# Reconcile latest origin/main through a normal, reviewed merge and rerun gates.
git push -u origin integration/final-release
gh pr create --base main --head integration/final-release --title 'Integrate and harden SolarOps Phases 1–3' --body-file docs/release/FINAL_MERGE_REPORT.md
# Inspect exact-head CI/review requirements before using the permitted merge method.
```

Do not use these commands to misrepresent the current partial checkpoint as a validated release. `~/Downloads/SOLOPS-final` is intentionally not created before a verified main merge.

## Executed checkpoint evidence

Tested code SHA: `ffae1ecf63d8d99b71f6a3d02ee6f531e275c253` (later report commits change documentation only). Baseline 122 backend tests; hardened 147 backend tests and 7 frontend tests. Commands are cwd-sensitive:

```sh
# From apps/api:
SOLAROPS_TEST_DATABASE_URL=postgresql+psycopg:///solarops_release_test_20261031 SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=solarops_release_test_20261031 .venv/bin/pytest
.venv/bin/ruff check app tests scripts
# With the private preview config loaded, read-only migration verification:
.venv/bin/alembic heads
.venv/bin/alembic current
# Generate API contracts under explicitly configured local/test settings:
.venv/bin/python scripts/export_openapi.py
# From apps/web:
npm ci --cache /private/tmp/solarops-npm-cache
npm test
npm run typecheck
npm run lint
npm run generate:api
npm run build
npm audit --audit-level=high --json
# From repository root:
SOLAROPS_TEST_DATABASE_URL=postgresql+psycopg:///solarops_release_test_20261031 SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=solarops_release_test_20261031 .pushgate/run.sh
```

Result: all available executed gate stages pass; aggregate remains INCOMPLETE 55.4/100 because ten required campaign entries are not run. Migration head e6a2b3c4d5f6. Two attempted browser tests failed at Chromium launch due sandbox permission, zero browser passes. Final npm audit 18 moderate/zero high/critical; Python audit 44 packages/zero known findings. Frozen dependency sync, contract regeneration and production build executed. Complete browser/operational requirements, coverage/mutation/load/restore and exact-head GitHub CI are not verified.

Historical QA CI success: https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41193327252. Latest unrelated frontend CI: https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41195733652; source inspection found success-printing lint/generator scripts, so its green result is not lint/contract evidence. No CI URL exists for the unpushed integration commit. Remote main remains a95533838fd4413233ed69edf2ce671260ea8c3a.
