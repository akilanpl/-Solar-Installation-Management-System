# Role Based Acceptance Report

Current completion audit, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`, integrated base `2f6e7122494ce214036d9baf98128411bdbea3c5`. Final commit/build identity and post-commit smoke are recorded in the delivered `FINAL_EXECUTION_MANIFEST.json`. Historical reports describe earlier candidates and are not current evidence.

| Role | Actual account | Browser observations | Limits |
|---|---|---|---|
|Customer|Separate verified synthetic customer|Signup, verify, login, enquiry, quotation acceptance, refresh/relogin; admin access denied|Payment blocked; downstream records absent|
|Sales|EMP-SALES-001|Same enquiry qualification, survey assignment/review, BOM quotation|Funded order not run|
|Technician|EMP-TECH-001|Assigned survey start, measurements, synthetic evidence upload, submission|No physical camera/offline/install acceptance|
|Warehouse staff|EMP-WH-001|Authenticated stock/picking/replacement empty states|No funded primary order or real goods|
|Warehouse manager|EMP-WHM-001|Distinct login and approval workspace|No populated approval workflow|
|Support|EMP-SUP-001|Authenticated inbox, lookup, warranty/repair/billing empty states|No populated post-installation case|
|Admin|EMP-ADMIN-001|Eight actual staff and real zero financial aggregates|No fabricated cash, revenue or staff availability|

Credentials: owner-only ignored `var/dev-seed-password.txt`, `var/demo-credentials.json`, and `var/completion-customer.json`. No password is included in this report. `demonstrate_local.py` provides repeatable seven-account HTTP verification through the real frontend proxy; final result is in the execution manifest. Browser support does not establish all business actions or all negative cases for each role.
