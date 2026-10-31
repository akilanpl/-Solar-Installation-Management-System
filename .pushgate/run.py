"""Run fixed executable campaigns; missing or partial evidence fails closed.

Campaign commands live in this reviewed source file, never in environment
variables or imported result files. Dedicated release campaign tests/scripts
must implement the named contract before that campaign can pass.
"""
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def source_state(root):
    return {
        "sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "dirty": bool(subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, text=True).strip()),
    }


def run_stage(root, folder, name, family, sev, directory, command, *,
              require_junit=False, prerequisites=(), timeout=600):
    """Execute once and collect only this invocation's XML and exit status."""
    xml = folder / f"{name}.xml"
    xml.unlink(missing_ok=True)
    logfile = folder / f"{name}.log"
    before = source_state(root)
    reason = None
    with logfile.open("w", encoding="utf-8") as log:
        log.write(json.dumps({"sha": before["sha"], "command": command}) + "\n")
        log.flush()
        missing = [path for path in prerequisites if not (root / path).is_file()]
        if missing:
            status, reason = "notrun", "Missing executable campaign source: " + ", ".join(missing)
            log.write(reason + "\n")
        else:
            try:
                env = dict(os.environ, PLAYWRIGHT_JUNIT_OUTPUT_FILE=str(xml),
                           SOLAROPS_RELEASE_SOURCE_SHA=before["sha"])
                outcome = subprocess.run(command, cwd=root / directory, stdout=log,
                                         stderr=subprocess.STDOUT, timeout=timeout, env=env, check=False)
                status = "pass" if outcome.returncode == 0 else "fail"
                if outcome.returncode:
                    reason = f"Command exited {outcome.returncode}"
            except (OSError, subprocess.TimeoutExpired) as exc:
                status, reason = "notrun", type(exc).__name__
                log.write(reason + "\n")
    rows = []
    if xml.exists():
        try:
            tree = ET.parse(xml)
            if tree.getroot().tag not in {"testsuite", "testsuites"}:
                raise ET.ParseError("Invalid JUnit root")
            cases = list(tree.iter("testcase"))
            suites = [node for node in tree.iter("testsuite") if not node.findall("testsuite")]
            declared = sum(int(node.get("tests", str(len(list(node.iter("testcase"))))))
                           for node in suites)
            if declared != len(cases):
                raise ET.ParseError("Partial JUnit output")
            for item in cases:
                state = ("fail" if item.find("failure") is not None or item.find("error") is not None
                         else "skip" if item.find("skipped") is not None else "pass")
                rows.append({"id": item.get("name", ""), "family": family, "sev": sev,
                             "status": state})
            if require_junit and (not cases or any(row["status"] != "pass" for row in rows)):
                status, reason = "fail", "JUnit is empty or contains failed/skipped tests"
        except (ET.ParseError, OSError, ValueError):
            status, reason = "fail", "Invalid JUnit output"
    elif require_junit and status == "pass":
        status, reason = "fail", "Successful command did not emit required JUnit"
    after = source_state(root)
    if before != after:
        status, reason = "fail", "Source changed while campaign ran"
    stage = {"id": f"stage-{name}", "family": family, "sev": sev, "status": status,
             "sha": before["sha"], "reason": reason}
    return [stage, *rows]


def mandatory_campaigns(root, folder, api_python):
    """Each named requirement has a fixed executable adapter and fresh JUnit.

    Existing ordinary unit tests are not credited as missing release campaigns.
    Missing dedicated adapters stay NOT RUN until their actual checks exist.
    """
    specifications = [
        ("migration-preservation", "D01", "tests/test_phase3_migrations.py"),
        ("edge-cases", "X01", "tests/release_campaigns/test_edges.py"),
        ("boundary-values", "V01", "tests/release_campaigns/test_boundaries.py"),
        ("load-performance", "P02", "tests/release_campaigns/test_load_performance.py"),
        ("resilience", "R02", "tests/release_campaigns/test_resilience.py"),
        ("concurrency-integrity", "C01", "tests/release_campaigns/test_concurrency.py"),
        ("backup-restore-operations", "O05", "tests/release_campaigns/test_operations.py"),
        ("phase3-full-acceptance", "D04", "tests/release_campaigns/test_phase3_acceptance.py"),
    ]
    campaigns = []
    for name, family, path in specifications:
        campaigns.append((name, family, "P0", "apps/api",
                          [api_python, "-m", "pytest", path,
                           f"--junitxml={folder}/{name}.xml"], [f"apps/api/{path}"]))
    for name, family, path in (
        ("customer-warranty-browser", "E04", "e2e/release/customer-warranty.spec.ts"),
        ("accessibility-compatibility", "Y01", "e2e/release/accessibility.spec.ts"),
    ):
        campaigns.append((name, family, "P0", "apps/web",
                          ["npx", "--no-install", "playwright", "test", path,
                           "--config=playwright.release.config.ts", "--reporter=junit"],
                          [f"apps/web/{path}", "apps/web/playwright.release.config.ts"]))
    for name, family, path in (
        ("outgoing-secret-history", "Z01", ".pushgate/campaigns/secret_history.py"),
        ("mutation-diff-coverage", "S03", ".pushgate/campaigns/coverage_quality.py"),
        ("main-ratchet-two-order-ci", "O07", ".pushgate/campaigns/baseline_ci_order.py"),
    ):
        campaigns.append((name, family, "P0", ".",
                          [api_python, path, "--junit", str(folder / f"{name}.xml")], [path]))
    return campaigns


def main():
    root = Path.cwd()
    initial = source_state(root)
    sha = initial["sha"]
    folder = root / ".pushgate/reports" / sha
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.json").unlink(missing_ok=True)
    tests = []
    api_bin = root / "apps/api/.venv" / ("Scripts" if os.name == "nt" else "bin")
    api_python = str(api_bin / ("python.exe" if os.name == "nt" else "python"))
    coverage_data = folder / "backend.coverage"
    coverage_json = folder / "backend-coverage.json"
    coverage_check = folder / "backend-coverage-check.json"
    for previous in (coverage_data, coverage_json, coverage_check):
        previous.unlink(missing_ok=True)
    stages = [
        ("gate-selftest", "S03", "P0", ".", [api_python, "-m", "unittest", "discover", "-s", ".pushgate", "-p", "test_*.py"]),
        ("lint-api", "S02", "P1", "apps/api", [str(api_bin / ("ruff.exe" if os.name == "nt" else "ruff")), "check", "app", "tests", "scripts"]),
        ("backend", "B03", "P0", "apps/api", [api_python, "-m", "coverage", "run", "--branch", "--source=app", f"--data-file={coverage_data}", "-m", "pytest", f"--junitxml={folder}/backend.xml"]),
        ("backend-coverage-export", "S03", "P0", "apps/api", [api_python, "-m", "coverage", "json", f"--data-file={coverage_data}", "-o", str(coverage_json)]),
        ("backend-coverage-check", "S03", "P0", ".", [api_python, ".pushgate/check_backend_coverage.py", "--coverage", str(coverage_json), "--config", ".pushgate/config.yml", "--output", str(coverage_check)]),
        ("frontend", "F01", "P1", "apps/web", ["npm", "test", "--", "--reporter=junit", f"--outputFile={folder}/frontend.xml"]),
        ("typecheck", "S03", "P0", "apps/web", ["npm", "run", "typecheck"]),
        ("lint-web", "S02", "P1", "apps/web", ["npm", "run", "lint"]),
        ("build", "S01", "P0", "apps/web", ["npm", "run", "build"]),
        ("dependency-audit", "S06", "P0", "apps/web", ["npm", "audit", "--audit-level=high", "--json"]),
    ]
    started = time.monotonic()
    for name, family, sev, directory, command in stages:
        print(f"Running {name}", flush=True)
        rows = run_stage(root, folder, name, family, sev, directory, command,
                         require_junit=name in {"backend", "frontend"})
        tests.extend(rows)
        if name == "backend-coverage-check" and coverage_check.exists():
            try:
                coverage_rows = json.loads(coverage_check.read_text(encoding="utf-8"))["tests"]
                tests.extend(dict(row, family="S03") for row in coverage_rows)
            except (ValueError, KeyError, TypeError):
                rows[0]["status"] = "fail"
                rows[0]["reason"] = "Invalid coverage checker output"
    missing = []
    for name, family, sev, directory, command, prerequisites in mandatory_campaigns(root, folder, api_python):
        print(f"Running required campaign {name}", flush=True)
        rows = run_stage(root, folder, name, family, sev, directory, command,
                         require_junit=True, prerequisites=prerequisites)
        tests.extend(rows)
        if rows[0]["status"] != "pass":
            missing.append(f"{name}: {rows[0]['status']} ({rows[0]['reason']})")
    final = source_state(root)
    source_valid = (bool(re.fullmatch(r"[0-9a-f]{40}", sha)) and not initial["dirty"]
                    and final == initial)
    tests.append({"id": "exact-clean-source", "family": "S01", "sev": "P0",
                  "status": "pass" if source_valid else "fail"})
    if not source_valid:
        missing.append("Exact source verification: checkout was dirty or changed during execution")
    report = {"sha": sha, "source_start": initial, "source_end": final,
              "seed": 20261031, "duration_seconds": round(time.monotonic() - started, 2),
              "tests": tests, "missing_evidence": missing}
    path = folder / "report.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    result = subprocess.run([sys.executable, ".pushgate/score.py", str(path)], check=False)
    print(f"Evidence: {folder}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
