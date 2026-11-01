# Retained product scope

| Phase | Retained implementation | Acceptance limits |
|---|---|---|
|1|Identity, roles, catalogue, enquiries, CSRF/session authentication|Full-source gates required|
|2|Qualification, assigned surveys, versioned quotes/BOM, acceptance, payment records, orders|Real provider certification outstanding|
|3|Location stock, exact serial movements, procurement, partial delivery, scheduling, installation evidence/signature, warranty|Shared lifecycle tests reconciled; real PostgreSQL core and dedicated acceptance catalogs pass|
|4A|Complaint triage, assignment, repair evidence, customer resolution/dispute/reopen|Combined lifecycle regression required|
|4B|Policy versions, serial coverage decisions, estimates, service invoices, replacement/return custody|Exact issue/install/return custody reconciled; focused regressions pass|
|4C|Immutable source-linked journals, reconciliation, revenue vs advances, costs/payables, profitability, subsidies/reports|No real financial transaction performed; approved recognition policy required|
|4D|Snapshots/outbox, finance invalidation, AI approval, weather/generation unavailable states|Live provider/telemetry acceptance outstanding|
|4E|Passkeys/MFA, offline intents/upload retries, extension terms/eligibility|Paid activation blocked pending legitimate extension settlement; flags/real authenticators unverified|
|Frontend|One Next.js apps/web, latest teammate survey/payment/receipt/mobile visual ports, protected role workspaces|Browser environment and complete populated journey acceptance incomplete|

No new feature phase was started. An existing module being present does not establish accepted release behavior.
