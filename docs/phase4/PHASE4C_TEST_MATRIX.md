# Phase 4C requirement-to-evidence matrix

All data is synthetic on task-owned PostgreSQL databases. No shared/production
schema is reset. Browser scenarios use real Next.js, FastAPI and PostgreSQL;
authentication in the managed-browser run uses the visible sign-in form.

| Requirement | Positive oracle | Negative/boundary oracle | Evidence |
| --- | --- | --- | --- |
| C1 balanced immutable journal | Exact debit/credit sums and stable source replay | SQL rejects update/delete, appending to committed postings and empty journals; concurrent event posts once; changed payload conflicts | `test_database_immutability_balance_seal_and_periods`, `test_concurrent_source_event_posts_once`, guard matrix |
| C1 period/rollback | Valid open-period posting, closed record preserved | Overlapping/invalid period, reopening, failed command leaves no cost/recognition artifacts | `test_source_invoice_duplicate_policy_period_rollback` |
| C2 original invoice/source tax | Original accepted totals, lines and tax retained | Missing policy/source, incomplete installation, sandbox cash, wrong payment, strict amount types | source-invoice, direct-receipt and guard tests |
| C2 cash versus revenue | Imported advance raises cash/advance only; allocation clears receivable | Over-allocation, reused event with changed content | `test_cash_advance_is_not_revenue_and_allocates_once` |
| C2 credits/reversal | Capped credit net/tax and compensating recognition reversal | Credit above balance, cross-order key reuse, unsupported dependent correction blocked | credit and profit/reversal tests |
| C3 labour/payable | Effective rate snapshot, 1001 paise/hour × 1 minute = 17 paise; approved cost and unpaid liability | Technician cannot approve; payout cap; cross-payable adjustment key conflict; wrong assigned job/rate | technician payable and guard matrix tests |
| C3 settlement evidence | Separate evidenced manual settlement clears adjusted payable | Approval leaves cash unchanged, over-settlement fails | PostgreSQL payable test; browser technician view |
| C4 profit/reconciliation | Ledger-derived positive and negative profit, all source IDs present | Missing actual valuation/recognition/time/attestation and newly discovered source changes remain incomplete | parameterized profit test; browser positive/loss and refreshed attestation |
| C5 subsidies | Owned case, versioned checklist, customer documents, sales review and supplied official-decision history | Missing documents, wrong owner, out-of-order decision, missing decision proof, frozen uploads and withdrawn-consent sales download | subsidy tests; customer/sales browser scenario |
| C6 dashboard/export | Live ledger totals, authorized job/record/journal drill-down, exact reproducible CSV bytes and SHA-256 | Staff role denial, no invented service provision, formula text escaped | roles/evidence, export-injection test; managed-browser download |
| Phase 4B adapter | Accepted bill keeps 12000 net + 2160 source tax = 14160 paise in browser | Unaccepted/missing/zero bills and unconsumed repair cost cannot appear reconciled | `test_approved_phase4b_service_bill_adapter`, browser source snapshot |
| Migration compatibility | Upgrade and downgrade/upgrade retain existing enquiry; no metadata drift | Inherited head pin extended, no old migration rewritten | inherited `test_phase3_migrations.py` |
| UI/build/contract | Existing unit tests, explicit typecheck/lint, production build and live OpenAPI comparison | Error/empty/incomplete UI, unauthorized role boundaries | checkpoint command logs and generated contracts |

Concurrency is bounded to two simultaneous database sessions. Full load,
resilience, accessibility and multi-browser/device campaigns are NOT RUN.
Current browser evidence is one actual managed IAB desktop session;
Playwright CLI launches were blocked by macOS sandbox permissions, not passed.
No mock or unit test is described as a real provider or government integration.
