"""Owner-pinned, dual-checkout first-main measurement; failed main stays uncertified."""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from bootstrap_protocol import (
    PIN_CONTROLLER,
    PIN_MAIN,
    REPOSITORY,
    digest,
    require,
    validate_certificate,
    validate_identity,
)

CONTROL = Path(__file__).resolve().parents[1]


def command(root, args, timeout=120):
    return subprocess.check_output(args, cwd=root, text=True, timeout=timeout).strip()


def api(endpoint):
    return json.loads(command(CONTROL, ["gh", "api", endpoint]))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state(root):
    return {
        "sha": command(root, ["git", "rev-parse", "HEAD"]),
        "dirty": bool(
            command(root, ["git", "status", "--porcelain", "--untracked-files=all"])
        ),
    }


def pins():
    return {key: os.environ.get(key, "") for key in (PIN_MAIN, PIN_CONTROLLER)}


def prior_initializations():
    # Explicit pagination: an API error is never treated as an empty history.
    endpoint = f"repos/{REPOSITORY}/actions/workflows/baseline-bootstrap.yml/runs"
    previous = []
    for page in range(1, 1001):
        runs = api(f"{endpoint}?per_page=100&page={page}")["workflow_runs"]
        for run in runs:
            if run.get("conclusion") == "success":
                previous.append(run["id"])
            # Rerunning an already successful attempt must not initialize twice.
            for attempt in range(1, run.get("run_attempt", 1)):
                old = api(
                    f"repos/{REPOSITORY}/actions/runs/{run['id']}/attempts/{attempt}"
                )
                if old.get("conclusion") == "success":
                    previous.append(f"{run['id']}/{attempt}")
        if len(runs) < 100:
            return previous
    raise ValueError("Unbounded workflow history; refusing incomplete provenance")


def trust(main):
    owner_pins = pins()
    run = api(f"repos/{REPOSITORY}/actions/runs/{os.environ['GITHUB_RUN_ID']}")
    live = api(f"repos/{REPOSITORY}/git/ref/heads/main")["object"]["sha"]
    validate_identity(
        dict(os.environ),
        owner_pins,
        run,
        state(main),
        state(CONTROL),
        live,
        prior_initializations(),
    )
    return owner_pins, run


def source_files(root):
    return command(root, ["git", "ls-tree", "-r", "HEAD"]).splitlines()


def collect(main, order):
    api_dir = main / "apps/api"
    normal = order.collect_nodes(api_dir)
    inventory = {
        "main_sha": state(main)["sha"],
        "source_files": source_files(main),
        "junit_cases": {
            "backend.xml": [list(order.node_tuple(n)) for n in normal],
            "ci-reverse-order.xml": [
                list(order.node_tuple(n)) for n in reversed(normal)
            ],
        },
    }
    # Collect dedicated pytest suites before running any tests.
    runner = load(main / ".pushgate/run.py", "measured_runner_inventory")
    folder = main / ".pushgate/reports" / state(main)["sha"]
    for name, _, _, directory, args, _ in runner.mandatory_campaigns(
        main, folder, sys.executable
    ):
        if directory == "apps/api":
            output = command(
                api_dir,
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-o",
                    "addopts=",
                    "--collect-only",
                    "-q",
                    args[3],
                ],
            )
            nodes = [
                line
                for line in output.splitlines()
                if line.startswith("tests/") and "::" in line
            ]
            require(nodes, "Empty campaign collection: " + name)
            inventory["junit_cases"][name + ".xml"] = [
                list(order.node_tuple(n)) for n in nodes
            ]
    web = main / "apps/web"
    listed = json.loads(command(web, ["npx", "vitest", "list", "--json"]))
    inventory["junit_cases"]["frontend.xml"] = [
        [str(Path(row["file"]).relative_to(web)), row["name"]] for row in listed
    ]
    for name, suite in [
        ("customer-warranty-browser", "customer-warranty.spec.ts"),
        ("accessibility-compatibility", "accessibility.spec.ts"),
    ]:
        report = json.loads(
            command(
                web,
                [
                    "npx",
                    "playwright",
                    "test",
                    "e2e/release/" + suite,
                    "--config=playwright.release.config.ts",
                    "--list",
                    "--reporter=json",
                ],
            )
        )
        cases = []

        def walk(s, parents, collected=cases, filename=suite):
            for spec in s.get("specs", []):
                for _ in spec["tests"]:
                    collected.append([filename, " ".join(parents + [spec["title"]])])
            for child in s.get("suites", []):
                walk(child, parents + ([child["title"]] if s.get("file") else []))

        for top in report["suites"]:
            walk(top, [])
        require(cases, "Empty browser collection")
        inventory["junit_cases"][name + ".xml"] = cases
    inventory["junit_cases"].update(
        {
            "outgoing-secret-history.xml": [
                ["Z01.secret-history", "candidate_ancestry_has_no_detected_secrets"]
            ],
            "mutation-diff-coverage.xml": [
                ["S03.coverage-quality", n]
                for n in ["diff_coverage_at_least_90", "mutation_score_at_least_60"]
            ],
            "main-ratchet-two-order-ci.xml": [
                ["O07.baseline-ci", n]
                for n in [
                    "accepted_main_baseline_and_ratchet",
                    "actual_same_sha_two_order_ci",
                ]
            ],
            "core-browser.xml": [
                [
                    "fresh-lifecycle.spec.ts",
                    "fresh customer through delivered serials, acknowledged installation, active warranty and closed complaint",
                ]
            ],
        }
    )
    return inventory


def order_stage(main, output):
    trust(main)
    order = load(
        CONTROL / ".pushgate/campaigns/baseline_ci_order.py", "bootstrap_order"
    )
    sha = state(main)["sha"]
    # Real normal-order evidence and complete reverse-order execution remain
    # mandatory. Only absence of a prior certified baseline is exempted.
    count = order.execute_two_orders(main, output.parent, sha)
    context = json.loads((output.parent / "campaign-context.json").read_text())
    require(
        context["sha"] == sha
        and context["source_start"] == state(main)
        and context["source_now"] == state(main),
        "Wrong measured context",
    )
    require(
        len(context["tests"]) >= 100
        and all(row["status"] == "pass" for row in context["tests"]),
        "Preceding absolute requirements failed",
    )
    trust(main)
    suite = ET.Element(
        "testsuite", name="main-ratchet-two-order-ci", tests="2", failures="0"
    )
    for name in ["accepted_main_baseline_and_ratchet", "actual_same_sha_two_order_ci"]:
        ET.SubElement(suite, "testcase", classname="O07.baseline-ci", name=name)
    ET.ElementTree(suite).write(output)
    (output.parent / "first-initialization-order.json").write_text(
        json.dumps(
            {
                "sha": sha,
                "prior_baseline": None,
                "exemption": "first baseline only",
                "tests_per_order": count,
            }
        )
    )


def measure(main):
    owner_pins, _run = trust(main)
    sha = owner_pins[PIN_MAIN]
    folder = main / ".pushgate/reports" / sha
    folder.mkdir(parents=True, exist_ok=True)
    order = load(
        CONTROL / ".pushgate/campaigns/baseline_ci_order.py", "bootstrap_collect"
    )
    inventory = collect(main, order)
    (folder / "inventory.json").write_text(json.dumps(inventory, indent=2))
    runner = load(main / ".pushgate/run.py", "frozen_main_runner")
    original = runner.run_stage

    def stage(root, target, name, family, sev, directory, args, **kwargs):
        # Budget corrections change neither commands nor assertions.
        if name == "backend":
            kwargs["timeout"] = 2400
        if name == "main-ratchet-two-order-ci":
            kwargs["timeout"] = 3600
            args = [
                sys.executable,
                str(CONTROL / ".pushgate/bootstrap.py"),
                "order",
                "--main",
                str(main),
                "--junit",
                str(target / (name + ".xml")),
            ]
        return original(root, target, name, family, sev, directory, args, **kwargs)

    runner.run_stage = stage
    os.chdir(main)
    sys.path.insert(0, str(main / ".pushgate"))
    code = runner.main()
    trust(main)
    return code


def seal(main):
    owner_pins, run = trust(main)
    sha = owner_pins[PIN_MAIN]
    folder = main / ".pushgate/reports" / sha
    inventory = json.loads((folder / "inventory.json").read_text())
    # Bind controller-run core evidence to the frozen main application source.
    core = CONTROL / "var/browser-ci"
    require(
        (core / "source-sha.txt").read_text().strip() == sha,
        "Wrong browser application source",
    )
    shutil.copy(core / "junit.xml", folder / "core-browser.xml")
    shutil.copy(
        core / "database-verification.json", folder / "core-database-verification.json"
    )
    names = {
        "report.json",
        "inventory.json",
        "backend-coverage-check.json",
        "backend-coverage.json",
        "diff-coverage-measured.json",
        "candidate-secret-history.json",
        "mutation-report.json",
        "core-database-verification.json",
    } | set(inventory["junit_cases"])
    files = {name: (folder / name).read_bytes() for name in names}
    cert = {
        "schema": 1,
        "kind": "first-accepted-main-baseline",
        "repository": REPOSITORY,
        "repository_id": 1440476764,
        "main_sha": sha,
        "controller_sha": owner_pins[PIN_CONTROLLER],
        "run_id": run["id"],
        "run_attempt": run["run_attempt"],
        "first_initialization": True,
        "prior_baseline": None,
        "files": {name: digest(blob) for name, blob in files.items()},
    }
    files["certificate.json"] = json.dumps(cert, indent=2).encode()
    score = load(main / ".pushgate/score.py", "bootstrap_score").score
    validate_certificate(
        files, owner_pins, run, None, sha, score, source_files(main), producing=True
    )
    destination = CONTROL / "var/baseline-certificate"
    require(not destination.exists(), "Certificate output already exists")
    destination.mkdir(parents=True)
    for name, blob in files.items():
        (destination / name).write_bytes(blob)
    print(
        "Absolute main certification validated; certificate awaits successful workflow completion."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "measure", "order", "seal"])
    parser.add_argument("--main", required=True, type=Path)
    parser.add_argument("--junit", type=Path)
    args = parser.parse_args()
    root = args.main.resolve()
    if args.action == "preflight":
        trust(root)
    elif args.action == "measure":
        return measure(root)
    elif args.action == "order":
        require(args.junit is not None, "JUnit path required")
        order_stage(root, args.junit)
    else:
        seal(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
