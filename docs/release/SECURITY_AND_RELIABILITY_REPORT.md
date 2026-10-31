# Security and reliability checkpoint

Checkpoint 2026-10-31. Committed candidate `9dba461ac921464064bd1bd3fd00c0701b68a710`; subsequent site-context improvements are being verified. This is an active acceptance checkpoint, not release approval.

Backend baseline: 159 passed. Latest full candidate run: **228 passed**, one Starlette/httpx deprecation warning. Measured line coverage 89.05%; branch coverage 65.72%. Branch/diff/mutation targets are not declared passed.

`gitleaks 8.30.1 git --redact=100 --log-opts='--all'` found two potential generic API-key exposures in unrelated teammate commit 68bc880: WeatherCard.jsx line 6 and SOLARFLOW_TECHNICAL_DOCUMENTATION.txt line 1507. No value is reproduced, tested or imported. Owner must review/rotate that key. Candidate outgoing-history scan at the earlier checkpoint found no secrets; rerun against the final commit is still required.

Backup: private ignored custom-format dump of the original preview. Restored into a new database; empty-database tests apply every Alembic migration, and upgraded restored records were compared using original columns. Latest head e2a8b9c0d1f2; latest preservation comparison covered 55 existing tables and ORM metadata matched. Original `solarops`, `solarops_test`, and prior preview data were not reset.

Production shared limiter is tested against PostgreSQL, not Redis mocks. Database outage test swaps only the isolated API's connection factory to an unavailable local port, observes 503, restores the factory and observes ready. It does not stop the user's PostgreSQL server.

Razorpay implementation follows [server order creation](https://raw.githubusercontent.com/razorpay/markdown-docs/master/api/orders/create.md), [raw webhook validation](https://raw.githubusercontent.com/razorpay/markdown-docs/master/webhooks/validate-test.md), and [authenticated payment fetch](https://raw.githubusercontent.com/razorpay/markdown-docs/master/api/payments/fetch-with-id.md). Provider transport mocks are restricted to tests; no default successful production adapter exists. Live keys are rejected. Authenticated refunds observed from provider data reduce verified balances; refund initiation is unavailable. Production provider/deployment evidence remains blocked.

Still required: realistic business workload latency, broader outage/rollback campaign, diff/branch coverage closure, mutation campaign, final outgoing-secret review and exact-head two-order CI.
