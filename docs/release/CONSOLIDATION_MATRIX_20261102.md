# SolarOps branch and PR consolidation matrix

Audit snapshot: 2026-11-02. All remote refs fetched and all 211 reachable commit/parent records inventoried. The local previous integration head is an ancestor of completion. A complete all-refs Git bundle is retained in ignored `var/consolidation-all-refs.bundle`. No source branch was deleted or force-pushed. Canonical runtime remains FastAPI `apps/api` plus Next.js `apps/web`; the old competing Vite/mock runtime is not introduced.

## Pull requests

| PR | Source classification | Final disposition for this cycle |
|---|---|---|
| #1 Phase 2 backend | Included in main and completion | Previously merged; retain |
| #2 Phase 2 integrity | Included in main and completion | Previously merged; retain |
| #3 actual frontend integration | Base included; three later commits were absent | Compatible delayed-response fix, scanner installer, provider-config helper and five test modules ported at 3701ebe. Newer canonical UTC/signature and evidence adapters retained. Closed as superseded by #11, with explanation; original branch preserved |
| #4 Phase 4A support | Functional base included; two later repair/publication commits were absent | Compatible fixes shared with #3 ported. Old alternative runners superseded by stricter canonical evidence code. 133 reconciled API cases pass locally. Closed with explanation; source branch preserved |
| #5 Phase 4B | Functional source and both parents of #8 already in main | Only unique head is a content-free merge commit; combined diff empty. Closed as superseded, branch preserved |
| #6 Phase 4C finance/admin (draft) | Exact head 5b1149c is an ancestor of main/completion | Closed as superseded, with explanation |
| #7 Phase 4D intelligence | Exact head 292b53d is an ancestor of main/completion | Closed as superseded, with explanation |
| #8 Phase 4E | Source parent 1668b6f is in main; merge was into the old dependent branch | Previously merged; no duplicate merge required |
| #9 Phase 1–4 integration | Merge 2f6e712 is current main, ancestor of completion | Previously merged; no repeat integration |
| #10 latest frontend recovery | Merge 3234181 is an ancestor of main | Previously merged; no repeat integration |
| #11 canonical completion | Current completion source and compatible repairs | OPEN DRAFT. No merge until genuine mandatory verification succeeds |

## Every current remote branch

| Branch | Head | Exact ancestor of main | Exact ancestor of completion |
|---|---|---|---|
| `origin/completion/solarops-20261102` | `d2bafeb4f8b2ca2d6cc089591426a8cf89075447` | No | Yes |
| `origin/feature/backend-workflows` | `b979ec6fa01974265faf0275f520b8fa41d33017` | Yes | Yes |
| `origin/feature/frontend-workplaces` | `fda30dbe826fe180cd76f2dbdfd55612aeecf97a` | No | No |
| `origin/feature/frontend-workspaces` | `81addc8539d69e5d39df3db545567c833350a87a` | Yes | Yes |
| `origin/feature/phase3-warehouse-installation` | `14d4e6bb055a39ff99e4842c69b2da125c86276c` | No | No |
| `origin/feature/phase4a-support` | `50e301e62dc75f6a91a5533675e8d62eb5c9f76a` | No | No |
| `origin/feature/phase4b-warranty-repair` | `798c6b4793abea67cc359b82167678f324b677f7` | No | No |
| `origin/feature/phase4c-finance-admin` | `5b1149c8f9805d0ec0edfd36406b48d04d2dd017` | Yes | Yes |
| `origin/feature/phase4d-intelligence` | `292b53d9f431568e950c0ed807c0795155625645` | Yes | Yes |
| `origin/feature/phase4e-enhancements` | `1668b6f5e5fc610c7bb6f98b1a6132b077dd832a` | Yes | Yes |
| `origin/fix/actual-frontend-integration` | `0e3c81a125e33068271184c7357f34869034751a` | No | No |
| `origin/fix/latest-frontend-recovery` | `ddf5d43bd9ed3fde58ce17dc48d9f3b3d110dba9` | Yes | Yes |
| `origin/fix/phase2-quotation-integrity` | `32cdc247a228a23f0e8d087914cb8f377d4acc6f` | Yes | Yes |
| `origin/integration/final-release` | `ebf107be1cc6996306b5756ccba42a1d96f087dc` | Yes | Yes |
| `origin/integration/solarops-complete-release` | `3234181e9f274df16af54b20c5c9362787554074` | Yes | Yes |
| `origin/main` | `2f6e7122494ce214036d9baf98128411bdbea3c5` | Yes | Yes |
| `origin/phase-1/foundation` | `81addc8539d69e5d39df3db545567c833350a87a` | Yes | Yes |
| `origin/test/qa-integration` | `d4e304e5ceb451fb069d54a17046aa6072749552` | No | No |

## Non-ancestor branches and duplicates

- `feature/phase3-warehouse-installation`: sole extra commit regenerates an older Phase 3 schema. Canonical generated client derives from the newer integrated OpenAPI contract; do not overwrite it with the historical generated file.
- `feature/phase4a-support` and `fix/actual-frontend-integration`: the compatible missing product and regression corrections were ported; publication logs and competing historical gate implementations do not replace current evidence adapters. UTC pool persistence and historical HMAC acceptance are already handled by newer canonical code; tests use the supported public boundary.
- `feature/phase4b-warranty-repair`: both merge parents are in main; the absent merge commit has no unique resolution content.
- `test/qa-integration`: documentation-only QA reports, not missing product behavior. Original source retained.
- `feature/frontend-workplaces`: original Vite branch remains preserved. Existing recovered shell/dock, wallet, actual-data dashboards, camera/upload UI, store/catalogue, transaction-card visuals and customer preferences cover earlier functional ports. Later reading ruler, local audio feedback, extra-large text, reading speed and pause/resume were additionally reconciled into the canonical customer assistant. Its speech reads actual page data and dictation stays an editable unsent draft. The mock POS routing/settlement behavior is superseded by real quotation/payment routes and explicit provider availability; no fictional payment success or subsidy payout is copied. Cosmetic source differences are not evidence of lost backend functionality, and screenshot fidelity is not certified by this matrix.
- Local `fix/actual-frontend-integration` at 03cbb014a70aece88ed5f4888ed102c0a690a65f is an ancestor of completion; no unique local work from that branch is discarded.

## Conflicts, approvals and merge boundary

GitHub reports #11 mergeable, with no unresolved review threads or requested reviewers at inspection. Main has no branch-protection rule or repository ruleset, but the user's mandatory acceptance condition still applies. No protection setting was changed. A successful accepted-main pushgate baseline does not exist for exact main 2f6e7122494ce214036d9baf98128411bdbea3c5. The existing baseline/ratchet rule is retained and fails closed. This matrix records code reconciliation and PR disposition; it is not a completed release or post-merge acceptance claim.
