# PR CI failure tracker

Initial inventory and repair started 2026-11-01 (Asia/Calcutta).

| PR | Branch | Failed check | Root cause | Fix status | CI status |
|---|---|---|---|---|---|
| #3 | fix/actual-frontend-integration | pushgate / gate | Unexecuted campaigns; stale/partial evidence; missing coverage; pooled timezone and form-response races | Partial repairs verified: 292 tests in both orders; coverage thresholds met; browser regression passed | Publication pending; release gate remains INCOMPLETE |
| #4 | feature/phase4a-support | pushgate / gate | Unexecuted mandatory campaigns | Pending sequential repair | Original CI passed; release gate INCOMPLETE |
| #5 | feature/phase4b-warranty-repair | pushgate / gate | Unexecuted mandatory campaigns | Pending sequential repair | Original CI passed; release gate INCOMPLETE |
| #6 | feature/phase4c-finance-admin | pushgate / gate | Unexecuted mandatory campaigns | Pending sequential repair | Original CI passed; release gate INCOMPLETE |
| #7 | feature/phase4d-intelligence | pushgate / gate | Unexecuted mandatory campaigns; merge conflicts | Pending sequential repair | Original CI passed; release gate INCOMPLETE |

No threshold, required check or business assertion has been removed. This
document is the implementation checkpoint; current remote outcomes are
consolidated in the workspace repair report after publication and monitoring.
