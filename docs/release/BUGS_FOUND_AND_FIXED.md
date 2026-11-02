# Bugs Found And Fixed

Current completion audit, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`, integrated base `2f6e7122494ce214036d9baf98128411bdbea3c5`. Final commit/build identity and post-commit smoke are recorded in the delivered `FINAL_EXECUTION_MANIFEST.json`. Historical reports describe earlier candidates and are not current evidence.

| ID | Priority | Finding | Action / verification |
|---|---|---|---|
|RUN-01|P1 local operation|Launcher hardcodes occupied 3061/8061 ports|Added validated `--api-port` / `--web-port`, preflight both listeners before spawning; occupied web-port test verifies no API child starts and original listener remains usable.|
|RUN-02|P1 local operation|Launcher announces URL before frontend readiness|Wait for HTTP 200 `/login`; detect early child exit and clean up only owned children.|
|ENV-01|External environment|Chromium aborts at macOS MachPortRendezvous bootstrap permission|Supported in-app browser used for manual acceptance; automated Playwright remains BLOCKED. No security controls bypassed.|
|ENV-02|External integration|No Razorpay test credentials/webhook secret|Preserved explicit disabled provider UI; no invented receipt/settlement.|
|QA-01|Test prerequisite|Backup campaign needs CREATEDB on dedicated test role|Granted only dedicated temporary local role for this campaign; revoked after successful 89-test campaign. Separate restore rehearsal matches all 100 tables.|

No P0 product defect was confirmed in the executed scope. This is not proof that no P0 exists: the funded primary journey and remaining acceptance are incomplete. Browser chooser tool returned after an unusually long delay; API 201 and saved evidence confirmed upload completion, so this was not classified as a proven product outage. Repeated sign-ins also hit the configured abuse limit; a fresh owned-server restart is required before the seven-account demonstration.

Regression additions: `apps/api/tests/test_complete_launcher.py` (four cases). `apps/api/scripts/demonstrate_local.py` reads real authorized data and verifies role/session boundaries without recording business events.
