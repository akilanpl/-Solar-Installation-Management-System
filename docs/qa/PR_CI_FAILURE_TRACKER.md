# PR CI failure tracker

Repair checkpoint, 2026-11-01 (Asia/Calcutta).

| PR | Branch | Failed check | Root cause | Fix status | CI status |
|---|---|---|---|---|---|
| #3 | fix/actual-frontend-integration | pushgate / gate | Missing release campaigns plus repaired evidence/timezone/form defects | Partial fixes pushed at 0e3c81a | All implemented stages pass; release BLOCKED 67.9/100 |
| #4 | feature/phase4a-support | pushgate / gate | 65.495% branch coverage; missing release campaigns; old qualification/UI test gaps | FIXED LOCALLY for implemented failures: 312 tests in both orders, branch 73.166%, browser 5 pass | Publication/remote verification pending |
| #5 | feature/phase4b-warranty-repair | pushgate / gate | 63.209% branch coverage; missing release campaigns | Pending sequential repair | Original gate failed |
| #6 | feature/phase4c-finance-admin | pushgate / gate | 65.839% branch coverage; missing release campaigns | Pending sequential repair against updated Phase 4B/4E base | Original gate failed |
| #7 | feature/phase4d-intelligence | pushgate / gate | 65.412% branch coverage; missing campaigns; base conflicts | Pending sequential repair against updated Phase 4B/4E base | Original gate failed |

Configured thresholds and required checks remain enforced. No PR is claimed
fully green while its mandatory release campaign evidence is incomplete.
