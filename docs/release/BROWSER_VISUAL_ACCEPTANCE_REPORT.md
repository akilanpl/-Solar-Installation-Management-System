# Browser Visual Acceptance Report

Current completion audit, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`, integrated base `2f6e7122494ce214036d9baf98128411bdbea3c5`. Final commit/build identity and post-commit smoke are recorded in the delivered `FINAL_EXECUTION_MANIFEST.json`. Historical reports describe earlier candidates and are not current evidence.

**PARTIAL, not final visual acceptance.** Rediscovered 67 pages; target matrix 201 route/viewports. In-app browser captured 216 observations of 57 distinct concrete routes; extra observations include different authorized roles on shared pages. All 51 static route patterns and six legitimately populated dynamic routes were reached. Ten remaining dynamic patterns lack valid populated records. Extra screenshots do not compensate for those missing patterns.

No document overflow was measured at 390/768/1280 in captured observations. Screenshots can include loading/empty states; `browser-observations.json` records loading flags. Representative customer enquiry, sales mobile, support mobile and admin desktop captures were visually inspected. Remaining captures are evidence for review, not individually certified WCAG/interaction passes. Full-scroll completeness is subject to the in-app browser screenshot implementation.

The real customer onboarding-to-quotation sequence and wrong-role admin denial were observed. Keyboard/modal, axe, Firefox/WebKit, device camera and full funded browser acceptance remain NOT RUN/BLOCKED. Playwright Chromium launch failed at `bootstrap_check_in ... MachPortRendezvousServer ... Permission denied (1100)`. The existing release suite remains assertion-bearing, and was not weakened. A supported CI run requires publishing this branch/dispatching an isolated runner; remote publication was not authorized.

| Source route | Captured widths | Recorded acceptance |
|---|---|---|
|`/admin`|390, 768, 1280|CAPTURED — partial acceptance|
|`/admin/pricing`|390, 768, 1280|CAPTURED — partial acceptance|
|`/admin/reports`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/bills/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/customer/bills`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/complaints/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/customer/complaints`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/enquiries/[id]`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/enquiries/new`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/equipment`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/estimates/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/customer/estimates`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/generation`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/installations`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/orders/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/customer/orders`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/payments`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/payments/razorpay`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/quotations/[id]`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/quotations`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/replacements`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/store`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/subsidies`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/support`|390, 768, 1280|CAPTURED — partial acceptance|
|`/customer/warranty-extensions`|390, 768, 1280|CAPTURED — partial acceptance|
|`/login`|390, 768, 1280|CAPTURED — partial acceptance|
|`/`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/enquiries/[id]`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/installations`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/orders/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/sales/orders`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/quotations/[id]`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/quotations`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/scheduling`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/subsidies`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/surveys/[id]`|390, 768, 1280|CAPTURED — partial acceptance|
|`/sales/surveys`|390, 768, 1280|CAPTURED — partial acceptance|
|`/security`|390, 768, 1280|CAPTURED — partial acceptance|
|`/signup`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support/billing`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support/estimates/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/support/estimates`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support/extensions`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support/intelligence`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support/lookup`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support/replacements/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/support/replacements`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support/tickets/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/support/warranty`|390, 768, 1280|CAPTURED — partial acceptance|
|`/support/weather`|390, 768, 1280|CAPTURED — partial acceptance|
|`/technician/install`|390, 768, 1280|CAPTURED — partial acceptance|
|`/technician/labour`|390, 768, 1280|CAPTURED — partial acceptance|
|`/technician/offline`|390, 768, 1280|CAPTURED — partial acceptance|
|`/technician`|390, 768, 1280|CAPTURED — partial acceptance|
|`/technician/repairs/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/technician/repairs`|390, 768, 1280|CAPTURED — partial acceptance|
|`/technician/surveys/[id]`|390, 768, 1280|CAPTURED — partial acceptance|
|`/technician/surveys`|390, 768, 1280|CAPTURED — partial acceptance|
|`/verify-email`|390, 768, 1280|CAPTURED — partial acceptance|
|`/warehouse/approvals`|390, 768, 1280|CAPTURED — partial acceptance|
|`/warehouse`|390, 768, 1280|CAPTURED — partial acceptance|
|`/warehouse/picking`|390, 768, 1280|CAPTURED — partial acceptance|
|`/warehouse/replacements/[id]`|—|BLOCKED — no legitimate populated fixture|
|`/warehouse/replacements`|390, 768, 1280|CAPTURED — partial acceptance|
