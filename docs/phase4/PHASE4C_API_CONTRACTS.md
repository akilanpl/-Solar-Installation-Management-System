# Phase 4C API changes

All paths below are under `/api/v1/finance`. Existing session cookies and CSRF
headers apply. JSON command bodies forbid unknown fields. Money uses integer
INR paise. UUID path/body fields are validated. See the checked-in generated
OpenAPI document and `apps/web/src/generated/schema.ts` for exact field schemas.

| Paths | Methods | Role |
| --- | --- | --- |
| `/evidence`, `/evidence/{id}` | POST multipart, GET binary | Owner/admin; linked consented subsidy documents additionally sales |
| `/records` | GET, optional `kind`, `order_id` | Admin all; other permitted roles receive scoped records |
| `/periods`, `/periods/{id}/close` | GET/POST, POST | Admin |
| `/policies` | POST | Admin |
| `/invoices`, `/invoices/{id}/recognize`, `/invoices/{id}/credits` | POST | Admin |
| `/receipts/import`, `/advances/allocate` | POST | Admin |
| `/journal`, `/journal/{id}/reverse` | GET, POST | Admin |
| `/labour-rates` | POST | Admin |
| `/timesheets`, `/timesheets/{id}/review` | POST | Assigned technician, admin respectively |
| `/payables/{id}/adjustments`, `/payables/{id}/settlements` | POST | Admin |
| `/costs`, `/completeness` | POST | Admin |
| `/subsidy-schemes` | POST | Admin |
| `/subsidies`, `/subsidies/{id}` | POST, GET | Customer creates own; customer/sales/admin scoped read |
| `/subsidies/{id}/documents` | POST | Owning customer |
| `/subsidies/{id}/events` | POST | Owner withdraws consent; sales/admin records evidenced review/submission/decision |
| `/dashboard`, `/reports/profit.csv` | GET | Admin |

Source identity supplies idempotency for invoices, receipts, recognition and
reviews. Commands with a `key` field use that key and an immutable content hash.
Settlements use the unique actual `bank_reference`. Successful replays return
the original record (the POST response remains 201); changed content produces
409 `idempotency_conflict`. Period creation rejects overlaps rather than using
an idempotency key. Duplicate identical closure is harmless; changed closure
proof conflicts.

Common safe failures are 401 unauthenticated, 403 role/CSRF denied, 404 inaccessible
or absent IDs, 422 malformed/unsupported money or command values, and 409 domain
state/policy/evidence/period/source conflicts. Responses retain the inherited
`error.code`, `error.message`, `error.details` envelope. Failed posting commands
roll back their domain records as well as journal lines.

`RecordResponse` has immutable kind, source key, source-order ID, actor, policy,
canonical payload, request hash and creation timestamp. `JournalResponse`
includes source record and event, date/period, reversal and account lines.
`DashboardResponse` includes ledger totals, nullable service liability,
subsidy state counts and job profit rows with completeness reasons and source
record IDs. The subsidy detail route includes case, state, missing-document list
and history. Binary evidence/export has `X-Artifact-SHA256`, `Cache-Control:
no-store` and `X-Content-Type-Options: nosniff`.

Regenerate using `.venv/bin/python scripts/export_openapi.py` in
`apps/api`, then `npm run generate:api` in `apps/web`. Environment variables must
identify the dedicated local database and a development secret. Regenerate both
files after combining any concurrent branch's routes; do not manually merge the
generated JSON/TypeScript. No provider webhook, charge, refund or government API
has been fabricated.
