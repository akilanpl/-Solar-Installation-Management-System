# Bugs Found And Fixed

Lifecycle follow-up, 2 November 2026 (Asia/Kolkata). Branch `completion/solarops-20261102`; baseline handoff `2b892fe3ec450ca1121afaaabdb1941d3f8716b9`. Final source/build SHA and post-commit smoke are in the delivered `FINAL_EXECUTION_MANIFEST.json`. Previous test counts are historical, not substituted for this run.

| ID / priority | Exact action / component | Expected vs baseline actual | Root cause and repair | Credentials needed? |
|---|---|---|---|---|
|PAY-01 P1|Customer payment → `quotations.tsx` / `/payments/intents`|Internal testing should proceed without claiming provider settlement; no UI existed|Connected explicit development-only intent/outcome interface to existing guarded service. Both public preview flag and authenticated backend capability required; production API denies simulation. Choices are pending, approval, failure or unknown; acknowledgment required.|No for internal simulation; yes for Razorpay|
|EQ-01 P1|My equipment after installation|Seven product policies activated; UI falsely said no equipment|Page read only separate Phase 4B service-policy coverage. Reused order-bound product coverage and kept both provenances separate; before/after browser proof.|No|
|CAL-01 P1|Create assigned job → calendar selector|New job should be selectable immediately; required refresh|Child calendar had an independent stale cache. Remount on parent job ID/status changes. Added focused frontend-contract browser regression; standalone execution blocked.|No|
|WAR-01 P1 clarity|Customer complaint warranty text|Product terms should not be conflated with older estimate|Explicitly label legacy order-level estimate and preserve its explanation; direct customer to serial product terms.|No|
|A11Y-01 P1|Mobile quotation/warehouse horizontal tables|Keyboard users could not focus scrolling regions|Added labelled focusable regions; axe rechecks pass.|No|
|A11Y-02 P1|Small text, auth focus, field errors|Contrast/focus/announcements below requirements|Darkened measured failing text and badges, restored input focus outlines and live validation errors. Stabilized video text contrast with a dark scrim; bounded contrast calculations preserved.|No|
|RUN-03 P1 local operation|Immediate launcher restart|Free port should restart; TIME_WAIT falsely rejected|SO_REUSEADDR preflight matches server restart behavior and still rejects live listeners. Five real-socket/argument tests pass.|No|

Unresolved external/environment boundaries: Razorpay credentials absent; Playwright Chromium macOS bootstrap denied. Browser file-picker calls sometimes returned very late; API persistence and UI readback confirmed uploads, so uncertain responses were not blindly retried. No confirmed P0 was found in the executed scope; untested variants are not certified defect-free.
