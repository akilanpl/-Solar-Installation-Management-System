"""Retrieve only the owner-pinned successful first-main certificate."""

import json
import os
import subprocess

from bootstrap_protocol import (
    PIN_CONTROLLER,
    PIN_MAIN,
    REPOSITORY,
    require,
    validate_archive,
    validate_certificate,
)


def read_owner_pins(root):
    # This separate credential is Variables:read for this repository only. Never
    # reuse an owner's broad local token or trust candidate-provided SHA values.
    token = os.environ.get("SOLAROPS_BASELINE_VARIABLES_READ_TOKEN", "")
    require(
        bool(token),
        "Owner-configured SOLAROPS_BASELINE_VARIABLES_READ_TOKEN required (repository Variables:read only)",
    )
    environment = dict(os.environ, GH_TOKEN=token)
    pins = {}
    for key in (PIN_MAIN, PIN_CONTROLLER):
        result = subprocess.run(
            ["gh", "api", f"repos/{REPOSITORY}/actions/variables/{key}"],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        require(
            result.returncode == 0,
            "Owner trust-root API denied; no environment-SHA fallback permitted",
        )
        pins[key] = json.loads(result.stdout)["value"]
    return pins


def accepted_bootstrap(root, repository, main_sha, api, execute, score):
    require(repository == REPOSITORY, "Unexpected baseline repository")
    # Candidate-controlled JSON/environment cannot set these trust anchors.
    pins = read_owner_pins(root)
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


if __name__ == "__main__":
    from pathlib import Path

    from bootstrap_protocol import SHA

    values = read_owner_pins(Path(__file__).resolve().parents[1])
    require(
        all(SHA.fullmatch(value) for value in values.values()), "Invalid owner pins"
    )
    print(
        "Owner-controlled trust-root API read verified; no certificate or release acceptance is implied."
    )
