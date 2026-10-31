# Security and reliability evidence

Application/test candidate `88766362fb7842b2da12be73d254d81cd627c9c8` on `fix/actual-frontend-integration`. Verification 2026-10-31. Main is not merged; Phase 4 has not started.

| Check | Observed result |
|---|---|
| Backend full regression | 269 passed, zero failures/errors, 113.54s; one Starlette/httpx deprecation warning |
| Gate self-tests | 10 passed; actual coverage thresholds/stage exit status preserved |
| Backend line coverage | 90.794% (80% floor) |
| Backend branch coverage | 70.39% (70% floor); PASS |
| Backend executable diff coverage | 92.746% against origin/main; 2672/2881 changed executable lines; frontend diff coverage not measured |
| Frontend | 27 tests; types/lint/generated contracts/optimized build pass |
| Backend dependency audit | 46 installed third-party packages audited, zero known vulnerabilities; first-party editable project excluded |
| Frontend dependency audit | 0 critical, 0 high, 18 moderate; moderate findings retained |
| Secrets | gitleaks 8.30.1 archive checksum verified; outgoing commits clear; all fetched refs contain 2 potential generic-key findings in unrelated 68bc880 |
| Backup/restore | Private snapshot before f3 restored into a fresh owned DB; all 57 tables matched; upgrade preserved 56 existing business tables and metadata parity; latest full rehearsal matched all 58 tables in 0.265s |
| Runtime | PostgreSQL readiness 200/up; real JSON correlation logs contain request ID, method, path, status and elapsed time; query/body/cookies/exception text excluded |
| Load | Locust 2.47.0, five users/0.2s pacing, 300s, loopback candidate only: 6944 requests, 0 failures, ~23.16 req/s, p50 12ms, p95 19ms, p99 30ms |
| Failure reproduction | First load run had 6885 requests/1 immediate post-login 401; deterministic response-boundary tests reproduced premature success and false 200 on failed commit; fixed and rerun |
| Mutation integrity | Seven selected in-memory critical fault probes killed after unchanged subset passed; not exhaustive changed-code mutation coverage |
| Resilience | Controlled connection-refusal/recovery and concurrent custody/calendar/OTP/abuse-limit regressions pass; no broad chaos/soak/deployment claim |

The two potential secret-history exposures are WeatherCard.jsx:6 and technical documentation:1507 in 68bc880. Values were neither imported nor printed. Owner must assess/rotate credentials if active; no history rewrite was performed.

Production SMTP/provider delivery, Razorpay sandbox acceptance, public signed webhook delivery, weather/maps/telemetry, production deployment/alerts, full stress/soak, comprehensive accessibility/cross-browser, full mutation and frontend diff coverage remain unverified or unavailable. No commercial production-readiness claim.
