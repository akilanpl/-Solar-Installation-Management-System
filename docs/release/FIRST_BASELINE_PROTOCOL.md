# First accepted-main baseline

This procedure measures an unchanged current `main` checkout using a separately
reviewed controller commit. It exempts only the unavailable prior certificate.
Every absolute campaign, coverage floor, security check, inventory integrity
check, score floor and full normal/reverse backend order remains mandatory.
A failed main measurement is not certified and cannot unblock a merge.

The repository owner sets `SOLAROPS_BASELINE_MAIN_SHA` to the exact live main SHA
and `SOLAROPS_BASELINE_CONTROLLER_SHA` to the reviewed controller SHA as GitHub
Actions repository variables before a normal push of that controller. The
workflow has no PR, arbitrary dispatch or externally supplied report input.
It checks authenticated repository ID, event, branch, workflow, run attempt,
owner actor, both clean source SHAs and live main before and after measurement.
Only one successful initialization is accepted, including earlier attempts of
a rerun. Failed attempts retain actual evidence and may be corrected and retried.
The controller variable is a trust root: write access must stay with the owner.
No certificate is accepted from a candidate's environment or PR artifact.

The frozen main runner executes all existing commands and assertions. Its backend
budget is extended to 2400 seconds; its final recursive-baseline adapter is
replaced in memory by the reviewed first-initialization adapter, which executes
the real reverse test order and verifies the preceding measured requirements.
Main source files are never overlaid. The additional fresh browser lifecycle
runs controller assertions against services built from frozen main, in a separate
empty PostgreSQL database with generated ephemeral credentials and no providers.

A certificate can be published only after absolute, fresh-browser and independent
SQL oracle steps succeed. It binds the complete Git source manifest, collected
JUnit inventories, actual coverage counts, mutation inventory and secret scan,
repository, both SHAs and exact run/attempt. Consumption requires the successful
owner-pinned workflow metadata and the GitHub artifact SHA-256 digest, then
revalidates every evidence file hash and metric. Missing, expired or altered
evidence fails closed. After initialization, candidates retain the original
90-point floor and two-point regression ratchet. A normal main merge certifies
against its verified previous first-parent main, then becomes the new baseline.
Repeated initialization or arbitrary replacement is prohibited.

Trust-boundary review must examine producer and consumer together. Repository
administrators can change variables or workflows; this protocol does not claim
to defend against a malicious repository owner. PR authors cannot impersonate
that owner-pinned initialization merely by uploading a similarly named artifact.
A complete independent review and successful hosted certification are required
before treating this protocol as release acceptance evidence.

## Secret-free authenticated owner-pin acquisition

The ordinary workflow token returned HTTP 403 for repository-variable REST
reads. A proposed dedicated-token path was independently rejected because a
candidate subprocess could inherit the credential; that change was reverted
before credential provisioning. No additional credential is required or used.

The consumer instead invokes the immutable reusable reader at
`35420870a93d68eb0a184201b667cf439d65f43f`. That workflow accepts no inputs,
performs no caller checkout/cache/dependency installation, reads GitHub's own
repository `vars` context, and signs only a canonical public pin manifest with
GitHub artifact attestations. Only its isolated job has OIDC/attestation-write
permissions; candidate tests receive read permissions and no extra secret.

The consumer checks the GitHub artifact digest, then runs GitHub CLI Sigstore
verification with the exact signer workflow/digest, source SHA/ref, repository,
predicate type and issuer, denying self-hosted signers. It additionally checks
certified repository ID, run invocation and attempt, exact signed file digest
and manifest identity. On PR runs the authenticated API run head may differ
from the tested synthetic merge SHA; both identities are validated in their
proper fields. Missing signatures, fields, capabilities or evidence fail closed.
An unsigned environment value or caller-selected signer is never a fallback.
The genuine hosted signature probe passed at run `41572508968`.

The verifier code and its fixed signer pin remain subject to independent review
for each owner-approved controller SHA. Signatures do not make arbitrary PR
edits to the verifier trustworthy. This is a release-review boundary, not a
claim of protection against a malicious repository owner.

## Existing-main measurement status

Run `41568604316` measured exact main
`2f6e7122494ce214036d9baf98128411bdbea3c5`: both backend orders executed 508 tests
with zero failures. The aggregate gate measured 69/100 INCOMPLETE. Legacy
browser campaigns had no populated preview/fixture environment; these are
infrastructure failures, not application defects. The separate real-services
fresh browser test independently failed serious customer-home text contrast
(4.19:1 and 4.47:1 against a 4.5:1 requirement). It stopped there; downstream
lifecycle and SQL oracle were not accepted. No certificate was issued.

The legacy campaigns still require a separate disposable, populated preview,
all sixteen concrete saved-record route mappings and their documented private
synthetic accounts before they can certify. Do not infer their results from the
separately passing fresh lifecycle on the completion branch. Until this
infrastructure and every genuine main defect pass, release remains HOLD.
