# End To End Workflow Matrix

Current completion audit, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`, integrated base `2f6e7122494ce214036d9baf98128411bdbea3c5`. Final commit/build identity and post-commit smoke are recorded in the delivered `FINAL_EXECUTION_MANIFEST.json`. Historical reports describe earlier candidates and are not current evidence.

| Transition | Outcome | Evidence / boundary |
|---|---|---|
|Registration → verification → login|PASS|Actual browser, development mailbox, synthetic customer|
|Enquiry → sales qualification|PASS|ENQ-2026-000005; customer refresh/relogin and separate sales role|
|Survey assignment → measurements → evidence|PASS|SUR-2026-000001; separate technician; labelled synthetic file|
|Sales approval → quotation → customer acceptance|PASS|QTN-2026-000001 v1; ₹94,872, approved survey/BOM persisted|
|Provider payment → order|BLOCKED|Razorpay test credentials + webhook secret absent; ₹0 verified; no order|
|Warehouse allocation → picking → delivery|NOT RUN in primary browser|Separate isolated API/DB regression is not the primary browser journey|
|Installation → customer acknowledgment → warranty|NOT RUN in primary browser|Requires funded confirmed order and valid equipment/evidence|
|Complaint → repair/replacement → resolution|NOT RUN populated browser|Regression exercises source-linked synthetic fixtures in separate test DB|
|Reporting/administration|PARTIAL|Actual zero-valued finance dashboard and eight staff observed|
|Refresh/logout/login persistence|PASS through quotation|Saved enquiry/survey/quotation survive refresh and role/session changes|

All physical measurements/events are explicitly synthetic software fixtures. No physical survey, payment, stock movement, delivery or installation is asserted. Existing internal payment simulation remains regression-only. It is not substituted for provider settlement.

Missing valid records block ten dynamic route patterns; their acceptance remains blocked rather than using fabricated IDs or orders.
