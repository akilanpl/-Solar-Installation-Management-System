# Original dirty checkout reconciliation

Inspected original `/Users/akilan/Downloads/SOLOPS` without modifying it. Its
tracked diff and untracked sources are separate from the clean Phase 4 branches.
Original HEAD: `a95533838fd4413233ed69edf2ce671260ea8c3a`.

## Retained unique behavior

- Rejected survey → linked resurvey draft. Restored as an explicit confirmed
  action on the current designed survey board, calling the existing authorized
  endpoint. The new draft opens by ID; rejected evidence/history is retained.
- Quotation withdrawal. Restored as an explicit confirmed action against the
  exact version. The existing server enforces order/payment/lifecycle rules.
- Direct detail pages: customer order/quotation, sales order/quotation/survey,
  technician survey. They reuse the current designed board components and fetch
  the specific record from its authenticated detail API. They do not filter only
  the first list page, so older valid records remain addressable.
- Sales order list and installation scheduling URLs. They reuse the current
  orders and scheduling/calendar boards. Existing navigation/visuals remain.

Main board references link to their detail pages; detail pages have return links.
Workspace role checks and server ownership remain the authority. No second
frontend or mock API was introduced.

## Superseded portions retained in source preservation, not applied verbatim

| Original source | Candidate equivalent / reason |
|---|---|
| `/api/v1/technicians`, TechnicianOption schema, directory tests | `/api/v1/workspace/technicians` already returns the same minimal fields, filters active technicians in SQL, and restricts sales/admin. Duplicating the API is unnecessary. |
| Customer/sales quotation lists, acceptance, revision requests, revisions, cash receipts, order conversion | Current Quotations component already implements these against actual APIs, with decimal money parsing and real Razorpay test-provider availability. |
| Order list/detail rendering | Current OrdersBoard additionally renders actual delivery status and recorded unit warranties. Old detail hardcoded that dispatch/installation had not occurred and scheduling was pending, regardless of current records. Those claims were not copied. |
| Sales scheduling page | Current SchedulingBoard and CalendarBoard support actual qualification/availability booking and job records. Old page displayed only the queue. |
| Technician survey detail, sales survey assignment/review | Current SurveysBoard already supports assignment, measurements, evidence upload/review and approval, and retains latest teammate survey workbench design. Old unrestricted appointment timestamp input was not restored over the qualified calendar workflow. |
| Customer quote sandbox-success controls | Not ported. Current provider verification/availability handling retained; no customer-declared settlement success added. |
| Old API aliases, shared basic UI/format helpers | Generated schema/current typed API, established designed components and decimal money parsing supersede the duplicates. |
| Old end-to-end workflow spec | Its stale selectors, fabricated short JPEG buffer and old sandbox path do not validate the current release. Preserve the source backup; current real-browser acceptance must cover the final application. |

Original working tree remains unchanged. Superseded source is not deleted; its
preservation artifact and provenance are managed by the integration owner.

## Verification

TypeScript and ESLint pass; existing frontend unit campaign: 47 passed across
8 files. Next.js production build passes, including all eight restored routes. Existing
backend regressions already exercise rejection/resurvey history and quotation
withdrawal rules; this frontend port changes no backend lifecycle logic.

These checks are not a claim that every new route has passed browser acceptance.
The final route-by-role browser matrix must include the eight restored routes and
exercise valid records, ownership denial, refresh and action failures.
