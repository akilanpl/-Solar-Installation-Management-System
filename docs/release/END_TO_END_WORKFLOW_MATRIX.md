# End To End Workflow Matrix

Lifecycle follow-up, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`; baseline handoff `2b892fe3ec450ca1121afaaabdb1941d3f8716b9`. Final source/build SHA and post-commit smoke are in the delivered `FINAL_EXECUTION_MANIFEST.json`. Previous test counts are historical, not substituted for this run.

Browser test names below are named **manual supported-browser cases**, not claims that Playwright executed. PNG + accessibility-tree evidence uses these exact names in delivered `lifecycle/`. Every case is backed by the normal API and PostgreSQL. Exact final source and readback are in the manifest.

| Browser case | Result | Roles | Persisted records | Screenshot / error evidence |
|---|---|---|---|---|
|J1 — accepted quotation to test payment and order|PASS|Customer; sales|QTN-2026-000001 v1, ORD-2026-000001; ₹94,872 simulation only|J1-test-payment-persisted; J1-order-confirmation-duplicate-rejected|
|J2 — warehouse preparation, allocation and picking|PASS|Warehouse staff|STK-000001…000008 fixtures; seven TEST-LIFECYCLE serials; STK-000009 pick|J2-insufficient-stock-rejected; J2-seven-serials-allocated; J2-double-pick-rejected|
|J3 — delivery and acknowledged installation|PASS|Warehouse; sales; technician; customer|DLV-2026-000001 confirmed; JOB-2026-000001 completed with uploaded file, OTP and summary-bound acknowledgment|J3-synthetic-delivery-confirmed; J3-completion-before-customer-acknowledgment-denied; J4-installation-completed|
|J4 — policy activation and customer visibility|PASS|Admin; customer; support|Seven active serial warranties, 2 Nov 2026–2 Nov 2028, synthetic 24-month terms bound before confirmation|J4-product-warranty-missing-from-equipment-RED; J4-product-warranties-visible-GREEN|
|J5 — complaint, repair, resolution and customer confirmation|PASS|Customer; support; technician|TKT-2026-000001 closed; RPJ-2026-000001 work submitted; exact resolution version 1 accepted|J5-support-owner-and-repair-assigned; J5-technician-repair-summary-persisted; J5-confirmed-resolution-closed|
|Actual Razorpay sandbox checkout/callback/webhook|BLOCKED|Customer/provider|Private test key/secret/webhook secret absent|No fabricated provider event|
|Standalone Playwright acceptance execution|BLOCKED|Runner|Chromium bootstrap permission denied before interactions|lifecycle-playwright.log|
|Replacement/estimate/billing variants outside no-parts repair|NOT TESTED|Various|Existing API/DB regressions pass; corresponding populated browser variants not executed|No replacement, charge or settlement invented|

Refresh, logout/login, a fresh server build and linked database readback preserved completed records. Customer and staff read the same IDs; another customer was denied order, coverage, job, complaint and payment access. A failed payment simulation preceded explicit approval; no unconditional success control exists.

Financial reporting sees the actual order with incomplete cost/revenue reconciliation, not fictitious profit. Its cash and recognized revenue remain ₹0 because internal simulation is not an evidenced bank/cash ledger settlement. Warehouse preparation requests retain their original intake marker under the existing schema; actual fulfilment is represented by delivery, consumed reservations and exact serial custody, not that static request field.
