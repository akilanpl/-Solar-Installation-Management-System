# Frontend handoff

Work in `apps/web` on `feature/frontend-workspaces`.

## Already running

- Sign in, sign up, and email verification. The development mailbox button is shown only when `NEXT_PUBLIC_SOLAROPS_ENV=development`. The API still returns 404 for that route outside development.
- Customer enquiry create, list, and detail. Data comes from `/api/v1/enquiries`.
- Sales queue and qualification.
- Admin employee list and provision form.
- Technician, warehouse, support, and the planned subpages render an empty state and the signed-in name. Do not add sample numbers.

## Rules

- Call the API through `src/lib/api.ts`. It sends the CSRF header and cookies.
- Types come from `src/generated/schema.ts`. After a backend contract change, run `npm run generate:api`.
- `src/lib/access.ts` decides which workspace a role may open. The login dropdown is not an input to that function. Keep it that way.
- Money on the wire is integer paise. Use `rupeesToPaise` and `formatInrFromPaise`.
- A new screen that has no API yet should use `PlannedWorkspace` or an empty state that says the data is not loaded.

## Next UI work

1. Survey and quotation screens against the planned routes, only after those routes exist. Until then, leave the planned pages empty.
2. Warehouse screens for draft and validate, matching the ledger rules in `docs/architecture/INTEGRATION_BOUNDARIES.md`.
3. Do not hide a button and call that authorization. The API returns 403 or 404; show `ErrorState`.

## Commands

```sh
npm ci
npm run dev
npm test
npm run typecheck
npm run lint
npm run build
```
