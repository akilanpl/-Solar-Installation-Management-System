# Full browser acceptance

Application/test candidate `88766362fb7842b2da12be73d254d81cd627c9c8` on `fix/actual-frontend-integration`. Verification 2026-10-31. Main is not merged; Phase 4 has not started.

The primary scenario uses distinct authenticated customer, sales, technician, warehouse, support and admin fixtures in `solarops_ultimate_preview_20261031`. All business events are labelled isolated software tests. No real charge, goods movement, site visit or installation occurred.

| Step | Primary scenario result |
|---|---|
| 1–3 Signup, verification, login | PASS: real backend signup, isolated development mailbox verification and customer session |
| 4 Enquiry | PASS: ENQ-2026-000002, customer-provided fixture site; persisted after reload |
| 5 Qualification | PASS: sales qualification, roof area/grid data and explicit fixture note |
| 6 Assignment/calendar | PASS: Kavya Rao, declared fixture hours/qualifications, booked 2026-10-31 20:36–21:06 Asia/Kolkata |
| 7 Survey/evidence | PASS: SUR-2026-000002, uploaded labelled synthetic PNG and recorded measurements |
| 8 Approval | PASS: sales reviewed authenticated file and approved only for isolated software acceptance |
| 9–10 BOM/quotation | PASS: QTN-2026-000001 version 1, stored BOM and total ₹94,872.00 |
| 11 Customer acceptance | PASS: owner accepted exact version; read back after application restart |
| 12 Provider test payment | BLOCKED: Razorpay key/secret/webhook configuration absent; verified total remains ₹0; no payment intent or receipt fabricated |
| 13–23 Order through warranty | NOT RUN in the primary browser scenario; requires step 12. API/DB regression flows are separate evidence and do not replace this browser journey |

Independent warehouse browser acceptance: original labelled fixture receipt STK-2026-000001 had three panels. Registered TEST-ULTIMATE-PANEL-001/002/003 through actual UI. Created and validated labelled transfer STK-2026-000002 with unit 001 selected. Reload and PostgreSQL confirm MAIN=2, SITE=1 and unit 001 at SITE. This is not fulfilment of the unfunded primary quotation.

Latest teammate survey workbench: real authorized records show 2 loaded surveys and 1 approved. Approved filter hides the other assigned survey. Mobile viewport 390×844 has document width 390. Desktop screenshot retains the genuine teammate workbench design.

Receipt preview: nontransactional chassis/LCD/paper/tear presentation; checked desktop and 390×844, Tab/Shift+Tab wrapping, Escape close/focus return, no invented settled amount/UTR. Stored receipt mode requires actual authorized receipt records.

Role smoke: customer, sales, technician, warehouse, support and admin use backend sessions. Support/finance/AI planned capabilities expose no fabricated records. Admin reads the real six-person roster and saved fixture policies/availability. Fast helper-driven administrator and sales sign-in attempts were rejected; reviewing/refilling the same unchanged credentials and submitting separately succeeded. It is retained as an unresolved browser/harness anomaly, not silently treated as a clean first-attempt pass.

Negative cases exercised in API/DB regressions include cross-user access, CSRF, inactive assignments, OTP attempts/expiry/replay, missing/tampered evidence, rejected acknowledgment, payment/provider mismatches, double allocation/pick, invalid serials/returns, overlapping bookings, rollback and controlled connection outage. Complete negative browser coverage, axe and Firefox/WebKit acceptance are NOT RUN.

Screenshots are copied into the user deliverable `screenshots/`; no private credentials or backups are included.
