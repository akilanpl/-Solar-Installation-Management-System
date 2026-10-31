# Phase 4C accounting policy boundary

These are implemented posting templates, not assertions of statutory compliance.
There is no default approved policy. An admin must record a named approval
reference, effective dates and explicit choices before any financial command.
Local acceptance approvals are labelled synthetic and have no business authority.
The business/accountant must approve the templates, recognition trigger, GST
snapshot treatment and evidence process before operational use.

| Approved event | Debit | Credit | Approval/source boundary |
| --- | --- | --- | --- |
| Original invoice | Receivable, gross | Deferred revenue, net; tax payable, source tax | Accepted order or accepted Phase 4B invoice; source snapshot retained |
| Earned revenue | Deferred revenue, remaining uncredited net | Revenue | Completed verified installation or submitted accepted service work; approval evidence |
| Unallocated verified cash | Cash | Customer advance | Existing manually verified non-test cash receipt with reference |
| Cash reconciled to invoice | Cash | Receivable | Same original order and no over-allocation |
| Advance allocation | Customer advance | Receivable | Same order; remaining advance and invoice bounds |
| Credit note | Deferred revenue or recognized revenue, net; tax payable, approved tax split | Receivable | Original cap, tax/net caps, approval artifact; service credits must match a real Phase 4B credit |
| Approved time | Labour cost | Technician payable | Assigned job, actual interval, effective rate snapshot and manager-approved minutes |
| Positive labour adjustment | Labour cost | Technician payable | Evidenced manager correction; negative adjustment reverses these sides |
| Actual consumed material valuation | Material cost | Inventory clearing | Completed installation dispatch or explicit Phase 4B repair-consumption movement, with actual-cost evidence |
| Attributable approved expense | Expense | Expense payable | Named source evidence and order attribution |
| Evidenced technician settlement | Technician payable | Cash | Actual bank reference and uploaded proof, capped at approved adjusted outstanding amount |
| Recognition reversal | Original credits become debits | Original debits become credits | One compensating posting, open current period, no dependent credits |

All calculations are integer INR paise, never floating point. Time approval uses
integer minutes bounded by recorded elapsed seconds; sub-minute time is not
silently rounded up. Labour proration is half-up: `(hourly_paise * minutes + 30)
// 60`. All source tax amounts are retained; this phase does not invent tax
rates, tax classification, subsidy entitlement or recognition rules. Explicit
Pydantic money fields reject booleans, fractions, numeric strings, negative
unsigned amounts and out-of-range values.

A unique source key plus content hash means a retry cannot become a second
posting or silently replace an earlier command. Posted records are immutable.
Corrections append events; no financial DELETE/PATCH endpoint exists. Posting
dates cannot precede the relevant invoice, completed work, stock movement,
payment receipt or payable. Period closure cannot be reopened by the API.

Job profit is recognized revenue minus actual valued material, approved labour
(including adjustments) and approved attributable expense. Cash received is not
profit. Neither customer advances nor payable approval establish revenue or a
bank transfer. Negative profits are supported and incomplete-data flags travel
with source-to-report reconciliation.

Subsidy scheme versions contain an official URL, captured source evidence,
effective dates and explicit required document types. A customer's consent is
recorded separately from sales review. Checklist completion is required before
review/submission. External references and artifacts are mandatory for review,
submission and recorded official decisions. Those records describe supplied
evidence; SolarOps never creates a government approval or disbursement.
