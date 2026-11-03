"""Verify a same-run owner-pin snapshot signed by an immutable isolated reader.

No candidate environment SHA values or extra credentials are accepted. GitHub
CLI performs Sigstore verification; this module checks certified identity and
complete run/source binding on its verified output, not unsigned predicate data.
"""

import json
import os
import tempfile
from pathlib import Path

from bootstrap_protocol import (
    PIN_CONTROLLER,
    PIN_MAIN,
    REPOSITORY,
    REPOSITORY_ID,
    SHA,
    digest,
    require,
    validate_archive,
)

SIGNER_SHA = "35420870a93d68eb0a184201b667cf439d65f43f"
SIGNER_PATH = REPOSITORY + "/.github/workflows/baseline-trust-reader.yml"
SIGNER_URI = "https://github.com/" + SIGNER_PATH + "@" + SIGNER_SHA
ISSUER = "https://token.actions.githubusercontent.com"
PREDICATE = "https://slsa.dev/provenance/v1"


def validate_verified_pins(blob, verified, context, run, artifact):
    document = json.loads(blob)
    require(
        context.get("GITHUB_REPOSITORY") == REPOSITORY
        and context.get("GITHUB_ACTIONS") == "true"
        and context.get("CI") == "true",
        "Actual repository Actions context required",
    )
    run_id, attempt = int(context["GITHUB_RUN_ID"]), int(context["GITHUB_RUN_ATTEMPT"])
    require(
        run.get("id") == run_id and run.get("run_attempt") == attempt,
        "Wrong authenticated pin run/attempt",
    )
    require(
        run.get("repository", {}).get("id") == REPOSITORY_ID
        and run["repository"].get("full_name") == REPOSITORY,
        "Wrong authenticated pin repository",
    )
    require(
        artifact.get("name") == f"baseline-owner-pins-{run_id}-{attempt}",
        "Wrong pin artifact identity",
    )
    # On PRs run.head_sha may be the PR head, while tested GITHUB_SHA is its
    # authenticated synthetic merge. Preserve that distinction explicitly.
    require(
        artifact.get("workflow_run", {}).get("id") == run_id
        and artifact["workflow_run"].get("head_sha") == run.get("head_sha"),
        "Foreign pin artifact",
    )
    expected = {
        "schema": 1,
        "repository": REPOSITORY,
        "repository_id": REPOSITORY_ID,
        "run_id": run_id,
        "run_attempt": attempt,
        "source_sha": context["GITHUB_SHA"],
        "source_ref": context["GITHUB_REF"],
    }
    require(
        all(document.get(key) == value for key, value in expected.items()),
        "Wrong signed pin document identity",
    )
    pins = document.get("pins", {})
    require(
        set(pins) == {PIN_MAIN, PIN_CONTROLLER}
        and all(isinstance(v, str) and SHA.fullmatch(v) for v in pins.values()),
        "Missing/invalid signed owner pins",
    )
    invocation = (
        f"https://github.com/{REPOSITORY}/actions/runs/{run_id}/attempts/{attempt}"
    )
    require(
        isinstance(verified, list) and bool(verified),
        "No cryptographically verified attestation",
    )
    matched = False
    for item in verified:
        value = item.get("verificationResult", {})
        cert = value.get("signature", {}).get("certificate", {})
        statement = value.get("statement", {})
        identity = {
            "issuer": ISSUER,
            "subjectAlternativeName": SIGNER_URI,
            "buildSignerURI": SIGNER_URI,
            "buildSignerDigest": SIGNER_SHA,
            "runnerEnvironment": "github-hosted",
            "sourceRepositoryURI": "https://github.com/" + REPOSITORY,
            "sourceRepositoryIdentifier": str(REPOSITORY_ID),
            "sourceRepositoryDigest": context["GITHUB_SHA"],
            "sourceRepositoryRef": context["GITHUB_REF"],
            "runInvocationURI": invocation,
        }
        if not all(cert.get(k) == v for k, v in identity.items()):
            continue
        require(value.get("verifiedTimestamps"), "Missing witnessed attestation time")
        require(
            statement.get("_type") == "https://in-toto.io/Statement/v1"
            and statement.get("predicateType") == PREDICATE,
            "Wrong attestation statement type",
        )
        require(
            statement.get("subject")
            == [{"name": "pins.json", "digest": {"sha256": digest(blob)}}],
            "Signed subject does not bind exact pin bytes",
        )
        matched = True
    require(matched, "Attestation signer, source or certified run identity mismatch")
    return pins


def verified_owner_pins(root, api, execute):
    context = dict(os.environ)
    run_id, attempt = (
        context.get("GITHUB_RUN_ID", ""),
        context.get("GITHUB_RUN_ATTEMPT", ""),
    )
    require(run_id.isdigit() and attempt.isdigit(), "Actual pin-reader run required")
    run = api(root, f"repos/{REPOSITORY}/actions/runs/{run_id}")
    artifacts = api(
        root, f"repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100"
    )["artifacts"]
    name = f"baseline-owner-pins-{run_id}-{attempt}"
    matches = [a for a in artifacts if a["name"] == name]
    require(len(matches) == 1, "Missing/ambiguous signed owner-pin artifact")
    artifact = matches[0]
    blob = execute(
        root,
        ["gh", "api", f"repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip"],
        binary=True,
    )
    require(len(blob) <= 1_000_000, "Unexpected owner-pin archive size")
    files = validate_archive(blob, artifact)
    require(set(files) == {"pins.json"}, "Unexpected pin archive entries")
    with tempfile.TemporaryDirectory(prefix="solarops-owner-pins-") as temporary:
        path = Path(temporary) / "pins.json"
        path.write_bytes(files["pins.json"])
        arguments = [
            "gh",
            "attestation",
            "verify",
            str(path),
            "--repo",
            REPOSITORY,
            "--signer-workflow",
            SIGNER_PATH,
            "--signer-digest",
            SIGNER_SHA,
            "--source-digest",
            context["GITHUB_SHA"],
            "--source-ref",
            context["GITHUB_REF"],
            "--cert-oidc-issuer",
            ISSUER,
            "--predicate-type",
            PREDICATE,
            "--deny-self-hosted-runners",
            "--format",
            "json",
        ]
        verified = json.loads(execute(root, arguments, timeout=120))
    return validate_verified_pins(files["pins.json"], verified, context, run, artifact)


if __name__ == "__main__":
    import subprocess

    def execute(directory, arguments, *, binary=False, timeout=120):
        result = subprocess.run(
            arguments,
            cwd=directory,
            capture_output=True,
            text=not binary,
            timeout=timeout,
            check=False,
        )
        require(
            result.returncode == 0,
            "Authenticated GitHub command failed; no unsigned fallback",
        )
        return result.stdout if binary else result.stdout.strip()

    def api(directory, endpoint):
        return json.loads(execute(directory, ["gh", "api", endpoint]))

    verified_owner_pins(Path(__file__).resolve().parents[1], api, execute)
    print(
        "Same-run immutable owner-pin signature, repository, source and run identity verified. No baseline or release certification is implied."
    )
