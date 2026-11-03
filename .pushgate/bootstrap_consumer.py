"""Retrieve only the owner-pinned successful first-main certificate."""

from bootstrap_protocol import (
    PIN_MAIN,
    REPOSITORY,
    require,
    validate_archive,
    validate_certificate,
)


def accepted_bootstrap(root, repository, main_sha, api, execute, score):
    require(repository == REPOSITORY, "Unexpected baseline repository")
    # Candidate-controlled JSON/environment cannot set these trust anchors.
    from owner_pin_attestation import verified_owner_pins

    pins = verified_owner_pins(root, api, execute)
    require(pins[PIN_MAIN] == main_sha, "Owner pin is not the exact required main SHA")
    runs = []
    for page in range(1, 1001):
        batch = api(
            root,
            f"repos/{repository}/actions/workflows/baseline-bootstrap.yml/runs?status=success&per_page=100&page={page}",
        )["workflow_runs"]
        runs.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError("Incomplete bootstrap history")
    require(len(runs) == 1, "Exactly one successful initialization required")
    run = api(root, f"repos/{repository}/actions/runs/{runs[0]['id']}")
    for attempt in range(1, run.get("run_attempt", 1)):
        old = api(
            root, f"repos/{repository}/actions/runs/{run['id']}/attempts/{attempt}"
        )
        require(
            old.get("conclusion") != "success", "Repeated successful initialization"
        )
    artifacts = api(root, f"repos/{repository}/actions/runs/{run['id']}/artifacts")[
        "artifacts"
    ]
    name = f"first-baseline-{main_sha}-attempt-{run['run_attempt']}"
    matches = [a for a in artifacts if a["name"] == name]
    require(len(matches) == 1, "Missing/ambiguous baseline certificate")
    artifact = matches[0]
    blob = execute(
        root,
        ["gh", "api", f"repos/{repository}/actions/artifacts/{artifact['id']}/zip"],
        binary=True,
    )
    files = validate_archive(blob, artifact)
    source = execute(root, ["git", "ls-tree", "-r", main_sha]).splitlines()
    return main_sha, validate_certificate(
        files, pins, run, artifact, main_sha, score, source
    )
