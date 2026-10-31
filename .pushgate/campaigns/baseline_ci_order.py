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
    verify_run_identity(root, sha, repository, run)
    return repository, run_id


def verify_run_identity(root, sha, repository, run):
    if os.environ.get("GITHUB_SHA") != sha:
        raise ValueError("GitHub checkout SHA differs from exact tested HEAD")
    if not run["path"].startswith(".github/workflows/pushgate.yml"):
        raise ValueError("Actions run does not belong to the pushgate workflow")
    if run.get("repository", {}).get("full_name") != repository:
        raise ValueError("Actions run repository identity mismatch")
    event = run["event"]
    if os.environ.get("GITHUB_EVENT_NAME") != event:
        raise ValueError(
            "Actions event context differs from authenticated run metadata"
        )
    if event == "push":
        if run["head_sha"] != sha:
            raise ValueError("Push run must certify its exact head SHA")
        return
    if event != "pull_request":
        raise ValueError(
            "Only authenticated push or pull_request runs may certify this checkout"
        )
    linked = run.get("pull_requests", [])
    if len(linked) != 1 or type(linked[0].get("number")) is not int:
        raise ValueError("PR run must identify exactly one actual pull request")
    reference = linked[0]
    number = reference["number"]
    if os.environ.get("GITHUB_REF") != f"refs/pull/{number}/merge":
        raise ValueError("PR checkout is not the expected synthetic merge ref")
    live = api(root, f"repos/{repository}/pulls/{number}")
    if live["state"] != "open" or live["base"]["repo"]["full_name"] != repository:
        raise ValueError("PR is closed or targets a different repository")
    head, base = live["head"]["sha"], live["base"]["sha"]
    if (
        reference["head"]["sha"] != head
        or reference["base"]["sha"] != base
        or run["head_sha"] not in {head, sha}
        or live["merge_commit_sha"] != sha
    ):
        raise ValueError(
            "PR head/base or synthetic merge changed since this Actions run"
        )
    parents = execute(root, ["git", "rev-list", "--parents", "-n", "1", "HEAD"]).split()
    if parents != [sha, base, head]:
        raise ValueError(
            "Tested synthetic merge parents do not match verified current PR base/head"
        )
    remote_merge = execute(
        root, ["git", "ls-remote", "origin", f"refs/pull/{number}/merge"]
    ).split()
    if remote_merge != [sha, f"refs/pull/{number}/merge"]:
        raise ValueError("Live GitHub PR merge ref no longer matches tested checkout")


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


def collect_nodes(api_dir):
    collected = execute(
        api_dir,
        [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
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
    return nodes


def node_tuple(node):
    filename, *parts = node.split("::")
    return (
        filename.removesuffix(".py").replace("/", ".")
        + ("." + ".".join(parts[:-1]) if len(parts) > 1 else ""),
        parts[-1],
    )


def passed_junit_nodes(output, nodes):
    tree = ET.parse(output)
    cases = list(tree.iter("testcase"))
    suites = [
        suite for suite in tree.iter("testsuite") if not suite.findall("testsuite")
    ]
    declared = sum(int(suite.get("tests", "0")) for suite in suites)
    observed = [(case.get("classname"), case.get("name")) for case in cases]
    if (
        declared != len(nodes)
        or observed != [node_tuple(node) for node in nodes]
        or any(
            case.find("failure") is not None
            or case.find("error") is not None
            or case.find("skipped") is not None
            for case in cases
        )
    ):
        raise ValueError(
            "JUnit does not match the full discovered exact node inventory/order with all passes"
        )
    return len(cases)


def verify_normal_order(root, folder, sha, nodes, gate_started_at):
    output = folder / "backend.xml"
    log = folder / "backend.log"
    header = json.loads(log.read_text().splitlines()[0])
    expected = [
        "-m",
        "coverage",
        "run",
        "--branch",
        "--source=app",
        f"--data-file={folder / 'backend.coverage'}",
        "-m",
        "pytest",
        "--ignore=tests/release_campaigns",
        f"--junitxml={output}",
    ]
    if header.get("sha") != sha or header.get("command", [])[1:] != expected:
        raise ValueError(
            "Normal-order backend log is not the fixed exact-SHA full coverage command"
        )
    started_at = header.get("started_at", 0)
    now = time.time()
    if (
        not 0 <= now - gate_started_at <= 3600
        or not gate_started_at <= started_at <= now
        or not started_at <= output.stat().st_mtime <= now
        or not started_at <= log.stat().st_mtime <= now
    ):
        raise ValueError(
            "Normal-order backend evidence is stale or predates this gate invocation"
        )
    return passed_junit_nodes(output, nodes)


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
    nodes = collect_nodes(api_dir)
    context = json.loads((folder / "campaign-context.json").read_text())
    verify_normal_order(root, folder, sha, nodes, context["gate_started_at"])
    # Normal order already executed in this gate. Reuse only its verified fresh
    # exact inventory, then run the opposite order once on CI's private service.
    reverse = list(reversed(nodes))
    output = folder / "ci-reverse-order.xml"
    output.unlink(missing_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            *reverse,
            f"--junitxml={output}",
        ],
        cwd=api_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=900,
        check=False,
    )
    (folder / "ci-reverse-order.log").write_text(result.stdout)
    if result.returncode or not output.is_file():
        raise ValueError(
            "Actual exact-SHA reverse-order campaign failed or emitted no JUnit"
        )
    passed_junit_nodes(output, reverse)
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

        def test_collection_overrides_double_quiet_project_addopts(self):
            nodes = [
                f"tests/test_collection.py::test_case_{index}" for index in range(100)
            ]
            with patch(__name__ + ".execute", return_value="\n".join(nodes)) as command:
                self.assertEqual(collect_nodes(Path(".")), nodes)
                arguments = command.call_args.args[1]
                self.assertEqual(arguments[arguments.index("-o") + 1], "addopts=")
                self.assertEqual(arguments.count("-q"), 1)

        def normal_fixture(self, folder):
            nodes = [
                "tests/test_example.py::test_first[a]",
                "tests/test_example.py::test_second",
            ]
            suite = ET.Element("testsuite", tests="2")
            for node in nodes:
                classname, name = node_tuple(node)
                ET.SubElement(suite, "testcase", classname=classname, name=name)
            output = folder / "backend.xml"
            ET.ElementTree(suite).write(output)
            began = time.time() - 2
            command = [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--branch",
                "--source=app",
                f"--data-file={folder / 'backend.coverage'}",
                "-m",
                "pytest",
                "--ignore=tests/release_campaigns",
                f"--junitxml={output}",
            ]
            header = {"sha": "a" * 40, "command": command, "started_at": began + 1}
            (folder / "backend.log").write_text(json.dumps(header) + "\n")
            return nodes, began, header

        def test_exact_fresh_normal_order_is_reused(self):
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                nodes, began, _ = self.normal_fixture(folder)
                self.assertEqual(
                    verify_normal_order(folder, folder, "a" * 40, nodes, began), 2
                )

        def test_stale_wrong_sha_and_partial_normal_evidence_fail(self):
            for failure in ("stale", "sha", "partial", "order", "skipped", "command"):
                with (
                    self.subTest(failure=failure),
                    tempfile.TemporaryDirectory() as directory,
                ):
                    folder = Path(directory)
                    nodes, began, header = self.normal_fixture(folder)
                    if failure == "stale":
                        began = time.time() + 1
                    if failure == "sha":
                        header["sha"] = "b" * 40
                    if failure == "command":
                        header["command"].append("-k=test_subset")
                    (folder / "backend.log").write_text(json.dumps(header) + "\n")
                    if failure in {"partial", "order", "skipped"}:
                        tree = ET.parse(folder / "backend.xml")
                        suite = tree.getroot()
                        if failure == "partial":
                            suite.remove(suite.findall("testcase")[-1])
                        elif failure == "order":
                            suite[:] = list(reversed(suite[:]))
                        else:
                            ET.SubElement(suite.findall("testcase")[0], "skipped")
                        tree.write(folder / "backend.xml")
                    with self.assertRaises(ValueError):
                        verify_normal_order(folder, folder, "a" * 40, nodes, began)

        def test_push_identity_and_synthetic_pr_identity(self):
            sha, head, base = "a" * 40, "b" * 40, "c" * 40
            repository = "owner/repo"
            run = {
                "path": ".github/workflows/pushgate.yml",
                "head_sha": sha,
                "repository": {"full_name": repository},
                "event": "push",
            }
            environment = {"GITHUB_SHA": sha, "GITHUB_EVENT_NAME": "push"}
            with patch.dict(os.environ, environment):
                verify_run_identity(Path("."), sha, repository, run)
            run.update(
                event="pull_request",
                head_sha=head,
                pull_requests=[
                    {"number": 3, "head": {"sha": head}, "base": {"sha": base}}
                ],
            )
            live = {
                "state": "open",
                "head": {"sha": head},
                "base": {"sha": base, "repo": {"full_name": repository}},
                "merge_commit_sha": sha,
            }
            environment.update(
                GITHUB_EVENT_NAME="pull_request", GITHUB_REF="refs/pull/3/merge"
            )
            for wrong in (
                None,
                "head",
                "base",
                "parents",
                "merge",
                "checkout",
                "event",
            ):
                with self.subTest(wrong=wrong):
                    actual = json.loads(json.dumps(live))
                    parents = f"{sha} {base} {head}"
                    ref = f"{sha} refs/pull/3/merge"
                    env = dict(environment)
                    if wrong in {"head", "base"}:
                        actual[wrong]["sha"] = "d" * 40
                    if wrong == "parents":
                        parents = f"{sha} {head} {base}"
                    if wrong == "merge":
                        ref = f"{'d' * 40} refs/pull/3/merge"
                    if wrong == "checkout":
                        env["GITHUB_SHA"] = "d" * 40
                    if wrong == "event":
                        env["GITHUB_EVENT_NAME"] = "pull_request_target"
                    with (
                        patch.dict(os.environ, env),
                        patch(__name__ + ".api", return_value=actual),
                        patch(__name__ + ".execute", side_effect=[parents, ref]),
                    ):
                        if wrong is None:
                            verify_run_identity(Path("."), sha, repository, run)
                        else:
                            with self.assertRaises(ValueError):
                                verify_run_identity(Path("."), sha, repository, run)

    outcome = unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    )
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main())
