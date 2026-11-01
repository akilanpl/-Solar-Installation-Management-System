# Phase 4 engineering contract

Status: VERIFIED for this written contract only. Phase 4 implementation is NOT IMPLEMENTED and must not begin as part of the integration mission.

## Entry gate

Do not start Phase 4 until Phases 1–3 release gates A–F are satisfied or a separately approved scope explicitly identifies the remaining blockers. This checkpoint has not passed those gates. Mandatory gaps include multi-location allocation, partial fulfilment, inspected returns, procurement chain, scheduling eligibility, serial-level policy warranty, complete browser workspaces and customer-to-warranty browser acceptance.

Remain a modular monolith using PostgreSQL, FastAPI/Pydantic, SQLAlchemy/Alembic and authenticated Next.js. New modules must use the same transaction, audit, authorization and generated-contract boundaries. A migration must be additive or have a tested, reviewed preservation/backfill plan. Never mutate historical quotations, ledger entries, financial postings or signed acceptance silently.

## Shared feature requirements

Every feature below must document actual data provenance and field ownership. All mutable transitions need actor, server UTC timestamp, source record/version, request/correlation ID and reason where applicable. Customer reads are owner-scoped; staff rights derive from persisted roles. Public signup cannot grant staff access. Evidence downloads require the same ownership checks as parent records.

Define request/response/status/error/idempotency contracts in FastAPI, export versioned OpenAPI and regenerate TypeScript. Document whether a command is pending, completed, failed, retryable or blocked. Never return success before durable internal state is committed, or describe provider queue acceptance as delivery or settlement. Retry handlers must deduplicate provider event IDs and business application IDs inside the posting transaction.

External providers must be real integrations with documented capability checks, authenticated server calls, request timeout, bounded retries and observable failure state. If unavailable, record BLOCKED and disable the action. Unit stubs belong in tests only. No speculative device faults, invented weather, real generation, distances, appointments, invoices, supplier acceptance or profit.

## Feature-specific contracts

### Support tickets and service resolution

- Data/models: actual customer, site, delivered serial, warranty policy and complaint; Ticket, TicketEvent, TicketAttachment, ResolutionAcknowledgment linked to the original order/asset.
- Transitions/roles/API: customer creates own `/tickets`; support triages OPEN → TRIAGED → ASSIGNED → IN_PROGRESS → WAITING_CUSTOMER → RESOLVED; owning customer confirms → CUSTOMER_CONFIRMED → CLOSED. Reopen and unresponsive escalation require recorded reason; technicians see only assigned work.
- Dependencies/failures/audit: real optional notification provider; unavailable notification must not close ticket. Preserve symptoms, fault code, attachments and every transition. Test IDOR, invalid/replayed/out-of-order transitions and refused resolution; acceptance requires customer acknowledgment visible after fresh login.

### Warranty-aware repair and replacement

- Data/models: exact serialized asset custody, confirmed delivery timestamp, versioned product coverage and exclusions; CoverageDecision snapshots policy, effective date and adjudicator; RepairJob, ReplacementAssetLink and compensating stock events.
- Transitions/roles/API: support assesses `/tickets/{id}/coverage`, authorized manager records exception with reason, assigned technician repairs; warehouse validates parts movement. Coverage cannot be inferred from a universal warranty duration.
- Dependencies/failures/audit: manufacturer decision is BLOCKED unless real integration or documented manual confirmation exists. Free/chargeable decision must remain reproducible from original policy. Test expiry boundary, exclusions, swapped serial, returned goods, repeated replacement and preserved asset history; acceptance requires exact unit-to-customer traceability.

### Out-of-warranty parts and labour billing

- Data/models: actual consumed material cost, approved price book and recorded technician time; ServiceEstimate, Approval, BillLine, TaxSnapshot and CreditNote.
- Transitions/roles/API: support prepares `/service-estimates`; customer accepts exact version; authorized finance issues invoice after billable work. Estimate → accepted/rejected/superseded, bill → issued/credited, never silently edited.
- Dependencies/failures/audit: approved tax/company policy; unavailable provider leaves payment pending/blocked. Snapshot unit amounts in INR paise and decimal quantities; no duplicate bill for retries. Test historical-price preservation, rounding, negative/duplicate lines and declined estimate; evidence includes itemized customer approval and persisted invoice.

### Customer-confirmed resolution

- Data/models: authenticated owning customer, actual work summary, parts and technician notes; immutable acknowledgment binds ticket/job/version and payload hash.
- Transitions/roles/API: customer reviews `/tickets/{id}/resolution-summary` then posts `/resolution-acknowledgments`; no technician boolean can impersonate customer acceptance. Reject stale summary, cross-ticket replay and unauthorized signatory.
- Dependencies/failures/audit: no delivery provider can replace authenticated acknowledgment. Refusal leaves ticket open or disputed; escalation is an explicit separate state. Tests cover refusal, replay and post-signature mutation; evidence is an audit-linked signed summary and fresh-session read.

### SysCache customer snapshots

- Data/models: actual PostgreSQL customer/site/installations/serials, policy warranty and recent authorized tickets. Snapshot key must include company/tenant, authorized scope and customer; store schema version, business version, generated_at and expires_at.
- Transitions/roles/API: support/admin scoped `/customer-snapshots/{id}`; customer only own supported snapshot. PostgreSQL remains authoritative. Transactional outbox records relevant customer/order/payment/serial/warranty/ticket changes for cache invalidation; TTL provides bounded recovery.
- Dependencies/failures/audit: optional real Redis or documented cache implementation; outage falls back to PostgreSQL, stale data is labeled. Exclude passwords, sessions, OTPs, payment tokens and unnecessary personal fields. Log metrics without sensitive payloads.
- Consistency/tests/evidence: test cross-role/scope isolation, invalidation after each relevant update, out-of-order events, simultaneous rebuilds, outage and schema-version rollover. Benchmark indexed PostgreSQL versus cache on the same authorized dataset with p50/p95, sample count, warm/cold policy, hit/miss rates and reproducible workload. No performance claim without measurements.

### Weather-aware operations

- Data/models: real provider response for consented/verified site location; ForecastSnapshot with source, issued_at, fetched_at, validity interval, units and uncertainty; Advisory linked to actual appointments.
- Transitions/roles/API: operations/assigned staff read `/weather/advisories`; advisory → acknowledged/dismissed; rescheduling is a separately authorized real appointment change.
- Dependencies/failures/audit: provider credentials, geocoding rights and real site coordinates; missing/stale/outage displays unavailable/stale, never synthetic forecast. Forecast is advisory, not a device-fault prediction. Test outage/staleness/units/region scoping and no automatic fabricated booking; evidence includes attributable provider test response and timestamp.

### Generation estimates and verified actual readings

- Data/models: estimates derive from documented capacity/orientation/weather/season/loss assumptions with model version and scenario interval; actual GenerationReading requires authenticated device/provider, meter ID, signed/source event ID, units and measured_at.
- Transitions/roles/API: customer-own/admin scoped `/generation/estimates` and `/generation/readings`; ingest → validated/rejected/quarantined. Corrections append provenance rather than overwrite raw readings.
- Dependencies/failures/audit: no provider means actual readings BLOCKED. Estimates visibly labeled and never counted as measurements. Test duplicate/out-of-order/negative readings, clock drift and isolation; evidence includes real provider sandbox/device payload authentication and measured-versus-estimated UI distinction.

### Skill-aware scheduling integration

- Data/models: active EmployeeProfile, independently maintained skills/validity, real working hours, leave, existing survey/install/repair appointments, daily cap and actual service region; SchedulingPolicy, Appointment and OverrideReason.
- Transitions/roles/API: sales/support get explainable `/assignments/eligibility`; create/confirm/reschedule/cancel appointments transactionally. Technician acknowledgment is distinct from assignment. PostgreSQL locks or exclusion constraints prevent concurrent overlaps across all job types.
- Dependencies/failures/audit: travel checks require real routing and verified coordinates. Otherwise clearly omit that capability, do not invent distance; no eligible worker returns no assignment. Authorized manual override requires reason and cannot bypass active-user/overlap safety. Test simultaneous bookings, working-hour/leave boundary, caps, expired skills and no eligible result; acceptance requires reproducible reasons and actual booking persistence.

### Revenue, expenses and per-job profit/loss

- Data/models: recognized revenue events, inventory cost snapshots consumed by job, actual approved technician labour/payable and attributable ExpensePosting; immutable AccountingEntry and reversal/adjustment links.
- Transitions/roles/API: authorized finance/admin approves and posts `/accounting/entries`; draft → approved → posted → reversed. Customer sees own permitted invoices, not company margin records.
- Dependencies/failures/audit: approved recognition/tax policy is required; bank cash settlement alone cannot recognize revenue. Profit = recognized revenue − consumed material cost − technician labour − attributable expenses. Advances are liabilities/unearned receipts until policy recognition; loss can be negative. No invented purchase cost or subsidy.
- Tests/evidence: currency/paise rounding, balanced postings, period close, duplicate events, concurrent posting and reversal; reconcile report to immutable source entries with per-job and period rollups. Acceptance requires exact source-to-report reconciliation, not a chart snapshot.

### Invoices and payment reconciliation

- Data/models: accepted sale/service quote, tax snapshot, immutable Invoice/InvoiceLine, real PaymentOrder, ProviderEvent, ReceiptApplication, Refund and CreditBalance.
- Transitions/roles/API: finance issues invoices; server creates provider order; verified webhooks/reconciliation move pending → processing → settled/failed/expired/unknown. Separate refund requested/accepted/settled states. Browser success alone does not verify payment.
- Dependencies/failures/audit: real selected Indian provider/test account with explicit UPI/card/netbanking/wallet/EMI capability; signed webhook verified before event application. No CVV/card secrets. Unknown/provider outage remains pending/blocked, retries deduplicate.
- Tests/evidence: bad signatures, mismatched currency/amount/order/customer, duplicate provider IDs, delayed events, overpayments and refunds; acceptance requires provider sandbox evidence plus ledger reconciliation. Live charges need separate explicit authorization.

### Government subsidy documents

- Data/models: actual applicant/customer consent, jurisdiction/scheme source and versioned checklist; SubsidyApplication, DocumentVersion, SubmissionRecord and DecisionEvidence.
- Transitions/roles/API: customer uploads own documents; sales validates/completes/submits manual evidence through `/subsidy-applications`; draft → submitted → information_requested → approved/rejected/withdrawn. Company cannot mark government approval without decision evidence.
- Dependencies/failures/audit: official supported integration or documented manual confirmation; otherwise external submission BLOCKED. Restrict sensitive documents, set retention and access audit. Test expired/missing/tampered documents, IDOR and false approval attempts; acceptance requires source-attributed decision history.

### Technician labour and payables

- Data/models: assigned job, server check-in, actual work time, approved labour rate/version, timesheet review; LabourEntry, Payable, Adjustment and actual SettlementEvidence.
- Transitions/roles/API: technician submits own timesheet; manager reviews; finance posts payable; settlement only from real authorized disbursement evidence. API `/timesheets`, `/payables` enforces split duties.
- Dependencies/failures/audit: no bank/payroll integration means transfer capability BLOCKED; recording a liability cannot claim a transfer. Preserve revisions, overtime decision and job allocation. Test overlapping/negative hours, duplicate liability, unauthorized approval and reversal; acceptance reconciles job labour cost to approved payable.

### Admin reports and export

- Data/models: authorized PostgreSQL views of real lifecycle/accounting records; ReportRun with source version, cutoff time, filters, currency and generated artifact hash.
- Transitions/roles/API: admin/finance read scoped `/reports` and request exports; queued → running → completed/failed/expired; only completed stored artifact is downloadable. Customer exports are separately owner-scoped.
- Dependencies/failures/audit: storage/job runner must be real; missing dependency returns unavailable, not placeholder success. Reports distinguish receivables/revenue/cash and unfinished/open repair stages. Protect spreadsheet formula injection and sensitive columns.
- Tests/evidence: source reconciliation, empty/large datasets, authorization, pagination/timezones, export integrity and failure retries; browser download must match persisted report totals and exact generation cutoff.

## Exit evidence required for every feature

Include migration-head and preservation proof, generated-contract reproducibility, meaningful unit/API/ownership/negative/concurrency tests, actual browser flow with refresh/fresh session, accessibility and responsive checks, provider sandbox evidence where relevant, and CI for the exact reviewed SHA. Review secrets, cost implications, retention and recovery. Never remove a required test or weaken a business invariant to pass a gate. Record VERIFIED/PARTIAL/BLOCKED/NOT IMPLEMENTED per capability; production readiness requires actual authorized staging evidence.

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


## Subsequent acceptance checkpoint — 2026-10-31

The historical result above is preserved. See RELEASE_GATE_RESULTS.md and FULL_BROWSER_ACCEPTANCE.md for tested candidate 8876636: 269 backend/27 frontend tests, 90.794% backend lines, 70.39% backend branches, and INCOMPLETE 57.8/100. Main is not merged and Phase 4 has not started.
