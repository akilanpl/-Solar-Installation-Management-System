# Phase 4C finance architecture

Phase 4C is an additive subledger in the existing synchronous FastAPI/SQLAlchemy
modular monolith. It does not replace authentication, inventory, ticketing,
Phase 4B billing, or the established request transaction. No service commits.
A successful request commits records and journal lines together; errors roll back.

## Persistence and transaction boundaries

Migration `4c1c2d3e4f50` follows the exact Phase 4B head `4b1c2d3e4f51`.
It adds five tables:

- `finance_periods`: nonoverlapping date intervals, evidenced permanent closure.
- `finance_records`: append-only typed domain events. Kind/source key is unique;
  an immutable canonical request hash detects conflicting retries. Order,
  customer, actor and approved-policy references are relational foreign keys.
  Type-specific upstream references and frozen source snapshots live in JSONB.
- `finance_entries`: unique source events, posting period/date, actor, source
  record, transaction identifier and optional unique reversal reference.
- `finance_lines`: normalized account debits and credits in BIGINT INR paise.
- `finance_evidence`: transactional PDF/image bytes, owner, SHA-256 and MIME.
  The size limit is enforced both at upload and in PostgreSQL.

PostgreSQL triggers reject updates/deletes to records, evidence, entries and
lines, reject additions to committed postings, enforce posting periods and
nonoverlap, and check nonzero balanced entries with deferred constraints at
commit. Thus an empty or unbalanced journal cannot become committed data.
Period closure receives its own append-only actor-stamped audit event.

A transaction-scoped advisory lock `404003` serializes finance writes and report
reads. Unique source/event constraints supply a second idempotency boundary.
This deliberately favors correctness over finance write throughput at the
inherited scale. Shared upstream workflows do not acquire this lock: only
finance-event consistency is serialized. Upstream integrations must retain
source immutability and are checked again during reconciliation.

## Adapters and provenance

`finance_service.py` reads accepted confirmed orders, original quotation tax and
line snapshots, customer-accepted Phase 4B service invoices, original credit
notes, completed installation/customer verification, submitted repair work,
verified non-sandbox cash receipts, and actual negative inventory movements.
It never changes those services. Material valuation needs approved evidence;
quoted material cost is never substituted for actual inventory cost.

All externally meaningful approvals are recorded by an authenticated role.
There is no provider integration in this base that can deliver a real signed
settlement event. Sandbox payments are rejected by finance; no webhook that
pretends to authenticate a provider is exposed. Bank settlements are explicitly
manual, evidenced records, not calls that transfer money.

Timesheets bind the submitting technician to the assigned job and recorded
work interval, reject overlaps, snapshot an effective approved labour rate,
and separate submission, manager review, adjustments and evidenced settlement.
Approval debits labour and credits a payable. Settlement alone affects cash.

## Authorization and UI

The existing admin role is the director/finance role; no new role or auth
rewrite is introduced. Only admins can manage money, journals, rates, periods,
policies and reports. Technicians can submit assigned time and see their own
rates, reviews, adjustments and settlements. Customers see their own bills and
subsidy cases. Sales sees subsidy records and can record reviews/submissions/
official decision evidence. Customer evidence is accessible to sales only when
linked to a subsidy case with consent not withdrawn. Guessed IDs do not grant
access. Existing cookie session and CSRF dependencies apply to every route.

Next.js screens reuse `Workspace`, `AppShell`, cards, fields, loading/error
states and the moss/ink visual system:
`/admin/reports`, `/technician/labour`, `/customer/subsidies`, `/sales/subsidies`.
TypeScript clients and generated contracts accompany the live routes. Record
and journal drill-downs expose source IDs and immutable evidence to authorized
reviewers. Monetary display converts paise only at the presentation boundary.

## Reports and data completeness

Revenue, cash, receivables, advances, deferred revenue, costs and payables sum
actual journal lines. Negative profit is retained. Profit rows include every
source record ID and explicit missing-data reasons. Missing stock valuations,
verified cash not imported, unimported service bills, unconsumed repair parts,
unimported Phase 4B credits, unreviewed time, unrecognized revenue, incomplete
installation and absent/outdated completeness attestations prevent a complete
reconciliation. Completeness attestations are human assertions supported by
evidence, not automated proof that every expense outside SolarOps is known.

Warranty/service liability valuation remains `null` with an explanation until
an approved provision policy and estimates exist. It is never reported as zero.
Subsidy counts come from the actual event histories. No hardcoded dashboard
business values or invented government payments exist.

CSV export has deterministic ordering, exact paise columns, source IDs, no-store
and nosniff headers, and a SHA-256 artifact header. Untrusted textual values
beginning with formula prefixes (including leading whitespace) are prefixed
with an apostrophe. Numeric negative profits remain numeric. CSV is the
supported report format; PDF is not implemented or claimed.

## Integration boundaries and deliberate release limits

Generated OpenAPI and TypeScript schemas must be regenerated after integrating
parallel branches. Migration heads must be reconciled with new additive merge
revisions, never by rewriting a shipped migration. The migration round-trip
head assertion and shell navigation are the other shared conflict surfaces.

This is a local development checkpoint. General manual journal corrections,
provider refunds, expense-payable settlement, arbitrary tax/recognition methods,
liability provisioning, policy revocation, evidence retention/deletion and
production signing/backup/monitoring require separate reviewed policies and
implementation. Unsafe unsupported actions are blocked rather than fabricated.
Recognition reversals are supported; invoice changes use credit notes and labour
changes use explicit adjustments. Re-recognition after reversal, or reversal of
credited recognition, requires a new approved adjustment workflow.
