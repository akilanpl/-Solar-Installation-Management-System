# SolarOps final project handoff

Frozen 3 November 2026 for source preservation and reversible Mac cleanup.
**Release INCOMPLETE. No product release merge or public deployment is authorized
by this handoff. Do not treat historical reports or passing component CI as full
main certification.**

## Source identities and pull requests

Repository: https://github.com/akilanpl/-Solar-Installation-Management-System

- Main at freeze: `6bc512bfb9f8ccc99dc3894ddb912ad32a3f640c` (README-only PR #12 merge).
- Complete product integration: `completion/solarops-20261102`, source
  `7ef9b0f9f9d94b6b61a8162221642da575be16e4`.
- Baseline repair implementation: `repair/accepted-main-baseline-20261103`,
  source `114cfb63027293e2701ffbdbf7e09cfa9848a826`; this handoff follows it.
- [PR #11](https://github.com/akilanpl/-Solar-Installation-Management-System/pull/11):
  OPEN DRAFT, canonical complete-product integration; mandatory gates blocked.
- [PR #13](https://github.com/akilanpl/-Solar-Installation-Management-System/pull/13):
  OPEN DRAFT, minimal baseline repair based on exact current main; not certified.
- PRs #1/#2/#8/#9/#10/#12 were merged previously. #3–#7 were reconciled and
  closed as superseded, with compatible missing fixes preserved in completion.
  See the completion branch's consolidation matrix for historical detail.

Use the complete-product branch to reconstruct the most complete application;
main alone does not contain all its later fixes. Preserve both repair commits
and the completion history. A later integration must reconcile both PRs rather
than blindly merge historical feature branches.

## Product and architecture

SolarOps manages rooftop solar enquiries through surveys, quotations, payment
records, order fulfilment, installation, serialized warranty and support.

- Next.js 15 / React / TypeScript frontend, Tailwind and recovered CSS components;
  role workspaces for customer, sales, warehouse staff/manager, technician,
  support and administration. Same-origin Next API proxy forwards to FastAPI.
- Python 3.12 FastAPI, Pydantic, SQLAlchemy and PostgreSQL 15/16; Alembic migrations
  retain identity, workflow, stock/custody, scheduling, support, warranty,
  finance, intelligence/cache and strong-auth records.
- Cookie sessions, CSRF, server-side role/ownership authorization, MFA/passkeys,
  idempotency, signed customer work acknowledgments and audit trails.
- Versioned policies/prices, finance and service billing, evidence uploads,
  offline synchronization and optional AI/weather/provider integrations.
- pytest/coverage, Vitest, Playwright/Axe, Ruff/ESLint/typecheck, generated OpenAPI
  contracts, Gitleaks and repository pushgate; GitHub Actions Linux PostgreSQL
  services provide independently executable verification.

Main and completion contain different stages of repair. Optional provider
features are not evidence of externally accepted integrations.

## Actual verification evidence

Complete product source `7ef9b0f…`:

- [API/web CI PASS](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41578270722):753 backend /88 frontend tests.
- [Fresh browser + PostgreSQL oracle PASS](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41578270767):signup/verification/login, enquiry, survey, quotation acceptance, isolated
  synthetic payment, order, warehouse/delivery, installation, seven unit
  warranties, complaint/repair/customer acceptance/closure. Includes role/CSRF/
  ownership denial, duplicate-transition guards and refresh/re-login persistence.
- [Pushgate FAIL](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41578270811):69/100 INCOMPLETE; legacy browser environment and accepted-main certification.
- [Failed first-main measurement](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41578270536):measured old exact main `2f6e712…`, not current `6bc512b…`;508 backend cases passed in both orders, but serious homepage contrast failed
  (4.19/4.47 against4.5), legacy campaigns failed, and no certificate was issued.

Initial repair `e6d21a3…`:

- [PR CI PASS](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41589573727):597 backend /85 frontend tests, real API and web jobs successful.
- [Push CI PASS](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41589554092).
- [Browser campaign](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41589554163) and
  [pushgate](https://github.com/akilanpl/-Solar-Installation-Management-System/actions/runs/41589554068)
  were still running at handoff preparation. Inspect terminal outcomes and
  artifacts; never infer pass from continue-on-error step labels.

Repair `114cfb6…` has independent read-only source approval,31 local gate unit
regressions and85 frontend tests passing, plus typecheck/ESLint/Ruff/actionlint
and committed-change secret scan. Clean local full gate measured69 INCOMPLETE:
508 backend tests pass, coverage exceeds unchanged80% line/70% branch floors,
local browser environment and hosted predecessor certification remain blocked.
Its fixture generator actually created16 dynamic-route records and authenticated
all required synthetic accounts in isolated PostgreSQL. Its changed browser
journeys require their own hosted execution; the older passing complete-product
run is not substituted for that evidence. Final remote run status may advance
after this document; use GitHub's exact SHA/run evidence.

## Fixed issues and remaining blockers

The repair darkens the three measured home text styles without relaxing Axe.
It supplies owned live API/Next services, a separate empty browser database,
private synthetic accounts, real saved dynamic-route fixtures, calendar
qualifications, receipt-linked serial registration, full installation before
complaints, repair evidence and customer acknowledgment before replacement
confirmation. It installs browser dependencies/Gitleaks, fixes time budgets and
owned process cleanup, and retains all seven journeys and720 accessibility cases.

**Still incomplete:** latest repair browser/accessibility acceptance, full
pushgate, a genuinely accepted exact-main first baseline, PR merges and fresh
postmerge main acceptance. Existing first-baseline circularity cannot justify
an unverified merge. [Recovery proposal](FIRST_BASELINE_RECOVERY_PROPOSAL.md)
is INACTIVE: any exceptional first repair merge requires genuine passing
absolute evidence, independent review and explicit future owner approval bound
to exact source/evidence. No predecessor score or certificate is fabricated.

No complete WCAG, production, full external-provider or final-main runtime
certification is claimed. Razorpay provider acceptance is BLOCKED until legitimate
test credentials exist. Isolated synthetic receipts/tests move no real money;
never represent them as successful Razorpay transactions.

## Reconstruct and run

Prerequisites: Git, Python3.12, uv, Node22/npm, PostgreSQL15/16. Clone and select
an explicitly recorded branch; no credentials are stored in GitHub:

```sh
git clone https://github.com/akilanpl/-Solar-Installation-Management-System.git solarops
cd solarops
git fetch origin
git switch --track origin/completion/solarops-20261102
cp .env.example .env
```

Follow [README standard startup](../../README.md#getting-started) and
[local PostgreSQL setup](../qa/LOCAL_POSTGRESQL.md). Create new dedicated
`solarops_dev` and `solarops_test` databases with a dedicated local role. Choose
its password interactively; generate a fresh32+character application secret and
put private values only in ignored `.env`. Development HTTP uses Secure=false;
production must retain HTTPS/Secure/explicit-origin requirements. Leave payment,
SMTP and other external provider keys unset for synthetic local use.

```sh
cd apps/api
uv sync --frozen
uv run alembic upgrade head
uv run python scripts/seed_dev.py
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
# Separate terminal, repository root:
cd apps/web
npm ci
npm run dev
```

Standard web:http://127.0.0.1:3000; API readiness:
http://127.0.0.1:8000/api/v1/ready. These are reconstruction instructions, not a
claim that this shutdown leaves a running application. Completion's documented
local launcher supports isolated preview startup and source identity checks;
see [local release runbook](LOCAL_RELEASE_RUNBOOK.md) and
[setup/recovery](LOCAL_SETUP_AND_RECOVERY.md). Historical3061/3063 previews are
not proof of final merged-main verification.

Staff seed creates only synthetic staff; customer signup and backend-gated local
mailbox verification are normal flows. Optional `scripts/seed_demo.py` creates
synthetic customer/enquiry data in development. Generated password/mailbox files
stay ignored and private. Never seed or run mutating tests against business data.
For repair CI, `.github/workflows/release-browser-repair.yml` creates a separate
`solarops_browser_release_ci` database and private fixtures through real commands;
its generator refuses unsafe/nonempty targets and external integrations. Do not
copy a local password file into GitHub or reuse the CI database as production.

Demo: customer signup→mailbox verification→enquiry; sales qualify and assign a
survey; technician submits evidence; sales issues quote; customer accepts;
authorized isolated synthetic payment/receipt funds order; warehouse registers
all received units and fulfils delivery; qualified technician records arrival,
OTP and evidence; customer acknowledges exact work; installation activates
warranty; customer raises complaint; support/technician resolve it and customer
accepts before closure. Every guard remains enforced.

## Tests and recovery

Use a separate explicitly disposable test database; pytest resets its schema.
Run `uv run pytest` and Ruff in apps/api; `npm test`, `npm run typecheck`,
`npm run lint`, `npm run build` in apps/web. Contract scripts export the actual
OpenAPI schema and generate frontend types; check diffs. From a clean checkout,
`.pushgate/run.sh --mode=ci` requires explicit test database configuration and
actual GitHub context for certification. macOS native browser execution here
was unavailable; use the maintained Linux Actions workflows, not security
workarounds. Missing/failed/skipped campaigns remain failures.

Before data upgrades, `pg_dump --format=custom` into private storage and verify
restore into a newly created isolated database. Never drop shared databases,
replace a live schema or delete signed/accounting records as rollback. GitHub
preserves source/migrations/templates/tests; private local config, local-only
raw evidence and database contents require separate protected backups. The
shutdown manifest identifies their local recovery location. Global PostgreSQL
services/databases, shared tooling and credentials must remain untouched.

At shutdown no further development or certification loop continues. Leave
unverified PRs open and use exact remote SHAs and stored evidence for handoff.
