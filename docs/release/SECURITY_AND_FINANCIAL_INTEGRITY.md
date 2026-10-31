# Security and financial integrity

No production accounts were changed and no live transaction was performed. Existing login/RBAC/ownership/CSRF protections remain. Request-scoped commits for integrated modules now occur before success responses. Security-sensitive grants and offline uploads retain reauthorization.

Additional durability fixes include enhanced MFA/offline/extension commit-before-response semantics and PostgreSQL UTC persistence across pooled rollbacks. Service consumables now use exact accepted-invoice stock delivery; anonymous serialized consumption fails closed in favor of explicit unit custody.

Fixed confirmed issues: arbitrary-reference paid warranty activation now fails closed; offline evidence intents/uploads persist exact bound bytes and safe retries; finance emits durable same-transaction cache invalidations; outbox duplicates no longer roll back unrelated pending finance work; replacement issue no longer fabricates installation/return; coverage decision replay normalizes UTC and invalidates after expiry or void.

22 additional PostgreSQL regressions passed for concurrency/idempotency, journal atomicity and database balance guards, immutable financial records, outbox conflict preservation, snapshot privacy, evidence ownership and MFA/strong-auth failure persistence. Anonymous API audit:90 protected GET endpoints returned401; health/ready/CSRF were public as intended, local absent mailbox returned404. Generated OpenAPI operation IDs are unique.

Gitleaks 8.30.1 found no secrets in candidate ancestry or any of the five approved Phase 4 source histories. The broader separate frontend history contains two findings for a non-placeholder weather key at commit68bc8805c6212c9417274b41a964165ccc51b7a1 (WeatherCard source and documentation). Values are redacted. That key was not copied into the canonical app; its owner should rotate/revoke it. No history rewrite was attempted.

Dependency audits:53 installed Python packages, no known vulnerabilities; npm initially 18 moderate, zero high/critical. Re-audit final lockfile after added accessibility tooling. No claim of exhaustive penetration testing, dependency safety forever, or provider acceptance.

GitHub main protection endpoint returned404 'Branch not protected' at inspection. Required review/check enforcement must be configured and verified before any merge. This session did not reduce or change repository settings. Source publication exception applies only to five exact commits, with audit records and draft PRs; it is not release acceptance.
