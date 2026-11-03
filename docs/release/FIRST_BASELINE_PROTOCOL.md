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

## Consumer credential prerequisite

The real hosted default-token probe returned HTTP 403. The ordinary
`GITHUB_TOKEN` with contents/actions read cannot read repository variables.
The owner must configure repository Actions secret
`SOLAROPS_BASELINE_VARIABLES_READ_TOKEN` using a fine-grained credential scoped
only to this repository with Variables:read (and GitHub's mandatory metadata
read). No contents write, Actions write, administration, deployment, provider or
production credential is needed. Do not paste the credential into chat, files,
logs or commits; configure it in GitHub's Actions secret settings. The consumer
uses it only in the repository-variable API subprocess. Missing/denied access
fails closed; candidate environment SHA values are never substituted. The
workflow access probe is diagnostic; the mandatory O07 campaign still fails if
this prerequisite or any prior certification evidence is absent.
