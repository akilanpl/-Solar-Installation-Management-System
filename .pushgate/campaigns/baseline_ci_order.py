"""Verify accepted main's genuine GitHub artifact, ratchet and two CI test orders.

No local historical score file or externally supplied result JSON is accepted.
GitHub context is checked against its live authenticated Actions run; baseline
artifacts must originate from a successful pushgate run at verified main SHA.
"""

import argparse
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def execute(root, args, *, binary=False, timeout=60):
    result = subprocess.run(
        args,
        cwd=root,
        capture_output=True,
        text=not binary,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise ValueError(
            f"Required command failed: {args[0]} {args[1] if len(args) > 1 else ''}; exit {result.returncode}"
        )
    return result.stdout if binary else result.stdout.strip()


def api(root, endpoint):
    return json.loads(execute(root, ["gh", "api", endpoint]))


def scorer(root):
    spec = importlib.util.spec_from_file_location(
        "release_gate_score", root / ".pushgate/score.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.score


def checked_context(root, folder, sha):
    path = folder / "campaign-context.json"
    context = json.loads(path.read_text())
    identity = {"sha": sha, "dirty": False}
    if (
        context["sha"] != sha
        or context["source_start"] != identity
        or context["source_now"] != identity
    ):
        raise ValueError("Runner campaign context is not the exact clean source")
    if not 0 <= time.time() - context["created_at"] <= 120:
        raise ValueError("Runner campaign context is not fresh for this invocation")
    rows = context["tests"]
    if len(rows) < 100 or any(row["status"] != "pass" for row in rows):
        raise ValueError(
            "All preceding real campaigns must pass; at least100 measured rows required"
        )
    if context["score"] != scorer(root)(rows):
        raise ValueError(
            "Runner candidate score does not match deterministic measured rows"
        )
    return context["score"]


def verify_ci(root, sha):
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("CI") != "true":
        raise ValueError(
            "Actual GitHub Actions CI execution required; local runs cannot certify CI order evidence"
        )
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if (
        not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
        or not run_id.isdigit()
    ):
        raise ValueError("Missing genuine GitHub run identity")
    remote = execute(root, ["git", "remote", "get-url", "origin"])
    match = re.fullmatch(
        r"(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?", remote
    )
    if match is None or match[1] != repository:
        raise ValueError("GitHub repository differs from checkout origin")
    run = api(root, f"repos/{repository}/actions/runs/{run_id}")
    # pull_request checkout may be a merge SHA differing from head_sha. Fail
    # closed; a push workflow on the candidate branch certifies its exact SHA.
    if (
        run["head_sha"] != sha
        or run["event"] != "push"
        or not run["path"].startswith(".github/workflows/pushgate.yml")
    ):
        raise ValueError(
            "This campaign must run in the real exact-SHA pushgate push workflow"
        )
    return repository, run_id


def baseline_score(root, repository, sha):
    live = execute(root, ["git", "ls-remote", "origin", "refs/heads/main"]).split()
    if len(live) != 2 or live[1] != "refs/heads/main":
        raise ValueError("Live main SHA could not be verified")
    main_sha = live[0]
    if execute(root, ["git", "rev-parse", "origin/main"]) != main_sha:
        raise ValueError("origin/main is stale; fetch and rerun")
    runs = api(
        root,
        f"repos/{repository}/actions/workflows/pushgate.yml/runs?branch=main&event=push&status=success&per_page=100",
    )["workflow_runs"]
    accepted = next(
        (
            run
            for run in runs
            if run["head_sha"] == main_sha and run["conclusion"] == "success"
        ),
        None,
    )
    if accepted is None:
        raise ValueError(
            f"No successful accepted-main pushgate baseline exists for {main_sha}; baseline cannot be invented"
        )
    artifacts = api(
        root, f"repos/{repository}/actions/runs/{accepted['id']}/artifacts"
    )["artifacts"]
    artifact = next(
        (
            item
            for item in artifacts
            if item["name"] == "pushgate-evidence" and not item["expired"]
        ),
        None,
    )
    if artifact is None:
        raise ValueError("Accepted-main pushgate evidence artifact is missing/expired")
    archive = execute(
        root,
        ["gh", "api", f"repos/{repository}/actions/artifacts/{artifact['id']}/zip"],
        binary=True,
    )
    if len(archive) > 50_000_000:
        raise ValueError("Baseline artifact unexpectedly exceeds50MB")
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        matches = [
            name
            for name in zipped.namelist()
            if name.endswith(f"{main_sha}/report.json")
        ]
        if len(matches) != 1 or zipped.getinfo(matches[0]).file_size > 10_000_000:
            raise ValueError(
                "Artifact does not uniquely contain the accepted-main report"
            )
        report = json.loads(zipped.read(matches[0]))
    if (
        report["sha"] != main_sha
        or report.get("decision") != "PASS"
        or report.get("missing_evidence")
    ):
        raise ValueError("Main artifact is not an accepted complete exact-SHA report")
    if report["score"] != scorer(root)(report["tests"]) or report["score"] < 90:
        raise ValueError(
            "Main artifact score fails deterministic verification or protected threshold"
        )
    if any(row["status"] != "pass" for row in report["tests"]):
        raise ValueError("Main artifact contains failed/unexecuted evidence")
    return main_sha, report["score"]


def execute_two_orders(root, folder, sha):
    url = os.environ.get("SOLAROPS_TEST_DATABASE_URL", "")
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    if (
        parsed.host not in {"127.0.0.1", "localhost"}
        or parsed.database != "solarops_test"
    ):
        raise ValueError(
            "CI order campaign requires workflow-owned local solarops_test PostgreSQL service"
        )
    api_dir = root / "apps/api"
    collected = execute(
        api_dir,
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "--ignore=tests/release_campaigns",
        ],
        timeout=120,
    )
    nodes = [
        line.strip()
        for line in collected.splitlines()
        if re.match(r"^tests/[^\s]+\.py::", line.strip())
    ]
    if len(nodes) < 100 or len(nodes) != len(set(nodes)):
        raise ValueError("Unable to discover at least100 distinct exact test node IDs")
    for name, order in (
        ("source-order", nodes),
        ("reverse-order", list(reversed(nodes))),
    ):
        output = folder / f"ci-{name}.xml"
        output.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *order, f"--junitxml={output}"],
            cwd=api_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=240,
            check=False,
        )
        (folder / f"ci-{name}.log").write_text(result.stdout)
        cases = list(ET.parse(output).iter("testcase")) if output.exists() else []
        if (
            result.returncode
            or len(cases) != len(nodes)
            or any(
                case.find("failure") is not None
                or case.find("error") is not None
                or case.find("skipped") is not None
                for case in cases
            )
        ):
            raise ValueError(
                f"Actual exact-SHA {name} campaign failed or emitted incomplete/skipped JUnit"
            )
        if execute(root, ["git", "rev-parse", "HEAD"]) != sha or execute(
            root, ["git", "status", "--porcelain"]
        ):
            raise ValueError("Source changed during actual CI two-order campaign")
    return len(nodes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    args.junit.parent.mkdir(parents=True, exist_ok=True)
    reasons = {}
    names = ("accepted_main_baseline_and_ratchet", "actual_same_sha_two_order_ci")
    try:
        if shutil.which("gh") is None:
            raise ValueError(
                "Authenticated GitHub CLI prerequisite missing: gh auth status"
            )
        sha = execute(root, ["git", "rev-parse", "HEAD"])
        if args.junit.resolve().parent != (root / ".pushgate/reports" / sha).resolve():
            raise ValueError("JUnit must be written in this exact-SHA gate directory")
        candidate = checked_context(root, args.junit.parent, sha)
        repository, run_id = verify_ci(root, sha)
        main_sha, baseline = baseline_score(root, repository, sha)
        if candidate < baseline - 2:
            raise ValueError(
                f"Measured candidate score {candidate} regresses beyond2points from accepted main {baseline}"
            )
        count = execute_two_orders(root, args.junit.parent, sha)
        (args.junit.parent / "baseline-ci-verified.json").write_text(
            json.dumps(
                {
                    "sha": sha,
                    "main_sha": main_sha,
                    "baseline_score": baseline,
                    "candidate_conservative_score": candidate,
                    "github_run_id": run_id,
                    "distinct_tests_per_order": count,
                    "orders": ["source", "reverse"],
                },
                indent=2,
            )
            + "\n"
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
        ET.ParseError,
        zipfile.BadZipFile,
    ) as error:
        reason = f"CI/baseline acceptance unavailable: {type(error).__name__}: {error}"
        reasons = {name: reason for name in names}
    suite = ET.Element(
        "testsuite",
        name="main-ratchet-two-order-ci",
        tests="2",
        failures=str(len(reasons)),
    )
    for name in names:
        case = ET.SubElement(suite, "testcase", name=name, classname="O07.baseline-ci")
        if name in reasons:
            ET.SubElement(case, "failure", message=reasons[name]).text = reasons[name]
    ET.ElementTree(suite).write(args.junit, encoding="utf-8", xml_declaration=True)
    for reason in set(reasons.values()):
        print(reason)
    return 1 if reasons else 0


def self_test():
    """Negative-path selftests; no CI pass or release artifact is fabricated."""
    import tempfile
    import unittest
    from unittest.mock import patch

    class Checks(unittest.TestCase):
        def test_local_execution_cannot_certify_ci(self):
            with (
                patch.dict(os.environ, {"GITHUB_ACTIONS": "false", "CI": "false"}),
                self.assertRaisesRegex(ValueError, "Actual GitHub Actions"),
            ):
                verify_ci(Path("."), "a" * 40)

        def test_stale_context_cannot_certify_candidate(self):
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                identity = {"sha": "a" * 40, "dirty": False}
                (folder / "campaign-context.json").write_text(
                    json.dumps(
                        {
                            "sha": "a" * 40,
                            "source_start": identity,
                            "source_now": identity,
                            "created_at": 0,
                            "tests": [],
                            "score": 100,
                        }
                    )
                )
                with self.assertRaisesRegex(ValueError, "not fresh"):
                    checked_context(folder, folder, "a" * 40)

        def test_dirty_context_cannot_certify_candidate(self):
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                identity = {"sha": "a" * 40, "dirty": True}
                (folder / "campaign-context.json").write_text(
                    json.dumps(
                        {
                            "sha": "a" * 40,
                            "source_start": identity,
                            "source_now": identity,
                        }
                    )
                )
                with self.assertRaisesRegex(ValueError, "exact clean"):
                    checked_context(folder, folder, "a" * 40)

    outcome = unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    )
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main())
