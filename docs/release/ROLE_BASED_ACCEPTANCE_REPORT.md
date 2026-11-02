# Role Based Acceptance Report

Lifecycle follow-up, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`; baseline handoff `2b892fe3ec450ca1121afaaabdb1941d3f8716b9`. Final source/build SHA and post-commit smoke are in the delivered `FINAL_EXECUTION_MANIFEST.json`. Previous test counts are historical, not substituted for this run.

| Role | Current browser result | Persisted consistency |
|---|---|---|
|Customer|PASS|Test-only payment intent/outcome; exact accepted quote/order; own installation summary acceptance; seven active product warranties; complaint version 1 confirmation and closed-case readback|
|Sales|PASS|Exact quotation version/amount confirmed once; duplicate confirmation rejected; guarded fixture calendar assignment|
|Warehouse staff|PASS|Eight labelled receipt fixtures; seven exact serials; eight allocations; pick once; duplicate/insufficient-stock rejection; confirmed delivery|
|Technician|PASS|Assigned order/equipment; mailbox-delivered OTP; upload/evidence; cannot complete before acknowledgment; completion; diagnostic/no-parts repair submission|
|Support|PASS|Same installation and serial policies; triage/owner/repair assignment; versioned resolution; closure only after customer confirmation|
|Admin|PASS for tested actions|Two labelled synthetic product policies and temporary fixture availability; actual order appears in financial reconciliation with missing valuation/revenue explicitly incomplete and no invented cash/profit|

Warehouse-manager login/approval page was historically verified; no new procurement/replacement approval campaign was executed. Seven-role HTTP auth/read/logout script remains available. Actual credentials remain in owner-only ignored var/dev-seed-password.txt, var/demo-credentials.json and var/completion-customer.json.

Negative checks PASS: missing CSRF, customer staff-roster denial, five cross-customer record reads returning 404, duplicate order, intent replay, identical outcome replay and conflicting outcome rejection. Full backend regression independently exercises broader role and transaction boundaries. Browser proof files use the exact manual case names in END_TO_END_WORKFLOW_MATRIX.md.
