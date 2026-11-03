"""First-baseline trust and evidence validation. Never accepts PR artifacts.

The only bootstrap exemption is a prior certificate: every absolute campaign,
complete inventory, coverage floor and actual reverse order is still required.
Repository variables are owner-managed trust roots, not workflow inputs.
"""

import hashlib
import io
import json
import re
import stat
import zipfile
from pathlib import PurePosixPath

REPOSITORY = "akilanpl/-Solar-Installation-Management-System"
REPOSITORY_ID = 1440476764
WORKFLOW = ".github/workflows/baseline-bootstrap.yml"
CONTROL_REF = "refs/heads/completion/solarops-20261102"
PIN_CONTROLLER = "SOLAROPS_BASELINE_CONTROLLER_SHA"
PIN_MAIN = "SOLAROPS_BASELINE_MAIN_SHA"
SCHEMA = 1
SHA = re.compile(r"^[0-9a-f]{40}$")
# These are the fixed canonical absolute campaigns, not caller-selected commands.
CAMPAIGNS = {
    "migration-preservation",
    "edge-cases",
    "boundary-values",
    "load-performance",
    "resilience",
    "concurrency-integrity",
    "backup-restore-operations",
    "phase3-full-acceptance",
    "customer-warranty-browser",
    "accessibility-compatibility",
    "outgoing-secret-history",
    "mutation-diff-coverage",
}
FAMILIES = set("SBADFEXVZPRCYO")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_identity(
    context, pins, run, main_state, controller_state, live_main, history
):
    """Pure validator. Callers obtain run/pins/history through authenticated REST."""
    main_sha, controller_sha = pins.get(PIN_MAIN), pins.get(PIN_CONTROLLER)
    require(
        bool(SHA.fullmatch(main_sha or ""))
        and bool(SHA.fullmatch(controller_sha or "")),
        "Owner pins are missing/invalid",
    )
    require(
        main_sha != controller_sha,
        "Application and reviewed controller must be distinct commits",
    )
    require(
        context.get("GITHUB_ACTIONS") == "true" and context.get("CI") == "true",
        "Trusted GitHub Actions required",
    )
    require(context.get("GITHUB_REPOSITORY") == REPOSITORY, "Wrong repository context")
    require(
        context.get("GITHUB_EVENT_NAME") == "push"
        and context.get("GITHUB_REF") == CONTROL_REF,
        "PR/dispatch/foreign-ref bootstrap prohibited",
    )
    require(context.get("GITHUB_SHA") == controller_sha, "Unreviewed controller SHA")
    require(str(run.get("id")) == context.get("GITHUB_RUN_ID"), "Wrong workflow run")
    require(
        str(run.get("run_attempt")) == context.get("GITHUB_RUN_ATTEMPT"),
        "Wrong run attempt",
    )
    require(
        run.get("repository", {}).get("full_name") == REPOSITORY
        and run.get("repository", {}).get("id") == REPOSITORY_ID,
        "Wrong repository identity",
    )
    require(
        run.get("event") == "push"
        and run.get("head_branch") == CONTROL_REF.removeprefix("refs/heads/"),
        "Untrusted workflow event/ref",
    )
    require(
        run.get("path", "").split("@")[0] == WORKFLOW
        and run.get("head_sha") == controller_sha,
        "Wrong workflow/controller provenance",
    )
    owner = REPOSITORY.split("/")[0]
    require(
        run.get("actor", {}).get("login") == owner
        and run.get("triggering_actor", {}).get("login") == owner,
        "Only repository owner may initialize",
    )
    require(
        main_state == {"sha": main_sha, "dirty": False} and live_main == main_sha,
        "Main source changed, wrong or dirty",
    )
    require(
        controller_state == {"sha": controller_sha, "dirty": False},
        "Controller source changed or dirty",
    )
    # History must include all successful prior runs/attempts. The caller fails
    # closed on pagination or attempt lookup failure, never treats it as empty.
    require(
        not history,
        "A successful baseline initialization already exists; replacement prohibited",
    )
    return main_sha, controller_sha


def validate_rows(report, score_function):
    require(bool(SHA.fullmatch(report.get("sha", ""))), "Invalid report source SHA")
    identity = {"sha": report["sha"], "dirty": False}
    require(
        report.get("source_start") == identity and report.get("source_end") == identity,
        "Report source is not exact/clean",
    )
    rows = report.get("tests", [])
    require(isinstance(rows, list) and len(rows) >= 100, "Incomplete test inventory")
    require(
        all(
            isinstance(r, dict)
            and r.get("status") == "pass"
            and r.get("sev") in {"P0", "P1", "P2"}
            and isinstance(r.get("family"), str)
            for r in rows
        ),
        "Failed, skipped, flaky or unexecuted evidence",
    )
    require(
        FAMILIES <= {r["family"][0] for r in rows if r["family"]},
        "Absolute test family missing",
    )
    require(not report.get("missing_evidence"), "Mandatory evidence is missing")
    require(
        report.get("decision") == "PASS"
        and report.get("score") == score_function(rows)
        and report["score"] >= 90,
        "Invalid score or protected threshold not met",
    )
    stages = {r["id"] for r in rows if r.get("id", "").startswith("stage-")}
    require({"stage-" + c for c in CAMPAIGNS} <= stages, "Absolute campaign omitted")
    require(
        {
            "stage-backend",
            "stage-backend-coverage-export",
            "stage-backend-coverage-check",
            "stage-frontend",
            "stage-typecheck",
            "stage-lint-api",
            "stage-lint-web",
            "stage-build",
            "stage-dependency-audit",
        }
        <= stages,
        "Static/build/security stage omitted",
    )
    return report["score"]


def check_ratchet(candidate, baseline):
    require(
        isinstance(candidate, (int, float))
        and not isinstance(candidate, bool)
        and 0 <= candidate <= 100,
        "Invalid candidate score",
    )
    require(
        isinstance(baseline, (int, float))
        and not isinstance(baseline, bool)
        and 0 <= baseline <= 100,
        "Invalid baseline score",
    )
    require(
        candidate >= 90 and candidate >= baseline - 2,
        "Candidate regresses beyond original ratchet/threshold",
    )


def validate_archive(blob, artifact):
    require(len(blob) <= 50_000_000, "Certificate archive too large")
    require(
        artifact.get("expired") is False
        and artifact.get("digest") == "sha256:" + digest(blob),
        "Expired or altered artifact",
    )
    files = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        total = 0
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            require(
                not path.is_absolute()
                and ".." not in path.parts
                and "\\" not in item.filename,
                "Unsafe archive path",
            )
            require(
                item.filename not in files
                and not stat.S_ISLNK(item.external_attr >> 16),
                "Duplicate/symlink archive entry",
            )
            require(
                not item.is_dir() and item.file_size <= 10_000_000,
                "Invalid/oversized certificate entry",
            )
            total += item.file_size
            require(total <= 50_000_000, "Expanded certificate archive too large")
            files[item.filename] = archive.read(item)
    return files


def validate_certificate(
    files,
    pins,
    run,
    artifact,
    expected_main,
    score_function,
    expected_source_files,
    *,
    producing=False,
):
    """Verify immutable artifact, source manifest, complete inventories and metrics."""
    require("certificate.json" in files, "Certificate missing")
    cert = json.loads(files["certificate.json"])
    require(
        cert.get("schema") == SCHEMA
        and cert.get("kind") == "first-accepted-main-baseline",
        "Wrong certificate type",
    )
    require(
        cert.get("repository") == REPOSITORY
        and cert.get("repository_id") == REPOSITORY_ID,
        "Wrong certificate repository",
    )
    require(
        cert.get("main_sha") == expected_main == pins.get(PIN_MAIN),
        "Wrong baseline SHA",
    )
    require(
        cert.get("controller_sha") == pins.get(PIN_CONTROLLER) == run.get("head_sha"),
        "Wrong reviewed controller",
    )
    require(
        run.get("repository", {}).get("id") == REPOSITORY_ID
        and run.get("repository", {}).get("full_name") == REPOSITORY,
        "Wrong run repository",
    )
    require(
        run.get("event") == "push"
        and run.get("head_branch") == CONTROL_REF.removeprefix("refs/heads/"),
        "PR-controlled evidence cannot certify main",
    )
    require(
        run.get("path", "").split("@")[0] == WORKFLOW
        and (
            (run.get("status") == "in_progress" and run.get("conclusion") is None)
            if producing
            else (
                run.get("status") == "completed" and run.get("conclusion") == "success"
            )
        ),
        "Bootstrap run not successful/trusted",
    )
    owner = REPOSITORY.split("/")[0]
    require(
        run.get("actor", {}).get("login") == owner
        and run.get("triggering_actor", {}).get("login") == owner,
        "Untrusted actor",
    )
    require(
        cert.get("run_id") == run.get("id")
        and cert.get("run_attempt") == run.get("run_attempt"),
        "Wrong certificate run/attempt",
    )
    if not producing:
        require(
            artifact.get("workflow_run", {}).get("id") == run["id"]
            and artifact["workflow_run"].get("head_sha") == pins[PIN_CONTROLLER],
            "Artifact from another run/controller",
        )
        require(
            artifact.get("name")
            == f"first-baseline-{expected_main}-attempt-{run['run_attempt']}",
            "Wrong artifact identity",
        )
    hashes = cert.get("files", {})
    require(
        set(hashes) == set(files) - {"certificate.json"} and hashes,
        "Incomplete/extra certificate evidence",
    )
    for path, sha in hashes.items():
        require(digest(files[path]) == sha, "Altered evidence: " + path)
    mandatory = {
        "report.json",
        "inventory.json",
        "backend.xml",
        "ci-reverse-order.xml",
        "frontend.xml",
        "backend-coverage-check.json",
        "backend-coverage.json",
        "diff-coverage-measured.json",
        "candidate-secret-history.json",
        "mutation-report.json",
        "core-browser.xml",
        "core-database-verification.json",
    }
    require(mandatory <= set(files), "Required certification evidence missing")
    report = json.loads(files["report.json"])
    require(report.get("sha") == expected_main, "Wrong report SHA")
    score = validate_rows(report, score_function)
    inventory = json.loads(files["inventory.json"])
    require(
        inventory.get("main_sha") == expected_main
        and inventory.get("source_files") == expected_source_files,
        "Incomplete/wrong source test inventory",
    )
    # XML must be complete, unskipped, and match collected inventory. Expected
    # tuples are captured before execution by the owner-pinned controller.
    import xml.etree.ElementTree as ET

    for filename, expected in inventory.get("junit_cases", {}).items():
        require(
            filename in files and isinstance(expected, list) and expected,
            "Missing collected/JUnit inventory",
        )
        root = ET.fromstring(files[filename])
        cases = list(root.iter("testcase"))
        observed = [[c.get("classname"), c.get("name")] for c in cases]
        require(
            (observed == expected)
            if filename in {"backend.xml", "ci-reverse-order.xml"}
            else (sorted(observed) == sorted(expected)),
            "Partial or reordered JUnit inventory",
        )
        suites = [s for s in root.iter("testsuite") if not s.findall("testsuite")]
        require(
            sum(int(s.get("tests", "0")) for s in suites) == len(expected),
            "Declared XML count mismatch",
        )
        require(
            all(
                not any(
                    c.find(tag) is not None for tag in ["failure", "error", "skipped"]
                )
                for c in cases
            ),
            "JUnit contains failures/skips",
        )
    expected_xml = {
        "backend.xml",
        "ci-reverse-order.xml",
        "frontend.xml",
        "core-browser.xml",
    } | {c + ".xml" for c in CAMPAIGNS}
    require(
        expected_xml <= set(inventory.get("junit_cases", {})),
        "Campaign inventory omitted",
    )
    require(
        len(inventory["junit_cases"]["backend.xml"]) >= 100
        and inventory["junit_cases"]["ci-reverse-order.xml"]
        == list(reversed(inventory["junit_cases"]["backend.xml"])),
        "Both full execution orders required",
    )
    coverage = json.loads(files["backend-coverage-check.json"])
    rows = coverage.get("tests", [])
    require(
        {r.get("id") for r in rows}
        == {"backend-line-coverage", "backend-branch-coverage"},
        "Missing coverage inventory",
    )
    measured = json.loads(files["backend-coverage.json"])
    require(
        measured.get("meta", {}).get("branch_coverage") is True
        and measured.get("files"),
        "Missing measured branch coverage",
    )
    totals = measured["totals"]
    for kind, covered_key, total_key, floor in [
        ("line", "covered_lines", "num_statements", 80),
        ("branch", "covered_branches", "num_branches", 70),
    ]:
        row = next(r for r in rows if r["id"] == "backend-" + kind + "-coverage")
        covered, total = totals[covered_key], totals[total_key]
        require(
            type(total) is int
            and type(covered) is int
            and 0 < total
            and 0 <= covered <= total,
            "Invalid measured counts",
        )
        require(
            row.get("status") == "pass"
            and row.get("threshold") == floor
            and row.get("covered") == covered
            and row.get("total") == total
            and covered / total * 100 >= floor,
            "Coverage requirement failed",
        )
    diff = json.loads(files["diff-coverage-measured.json"])
    require(
        diff.get("sha") == expected_main
        and diff.get("threshold") == 90
        and diff.get("percent", -1) >= 90,
        "Diff coverage threshold failed",
    )
    require(
        json.loads(files["candidate-secret-history.json"]) == [],
        "Secret findings present",
    )
    mutation = json.loads(files["mutation-report.json"])
    require(
        mutation.get("sha") == expected_main
        and mutation.get("planned", 0) >= 15
        and mutation.get("errors") == 0
        and mutation.get("kill_percent", -1) >= 60
        and mutation.get("decision") == "PASS",
        "Mutation evidence failed",
    )
    mutants, planned = mutation.get("mutants", []), mutation["planned"]
    require(
        len(mutants) == planned
        and len(set(mutation.get("inventory", []))) == planned
        and {m.get("id") for m in mutants} == set(mutation["inventory"]),
        "Partial mutation inventory",
    )
    require(
        all(m.get("status") in {"killed", "survived"} for m in mutants)
        and mutation.get("baseline", {}).get("status") == "passed",
        "Unexecuted mutation",
    )
    killed = sum(m["status"] == "killed" for m in mutants)
    require(
        mutation.get("killed") == killed
        and abs(mutation["kill_percent"] - killed / planned * 100) < 0.001,
        "False mutation score",
    )
    require(
        json.loads(files["core-database-verification.json"]).get("status") == "PASS",
        "Independent database oracle failed",
    )
    require(
        cert.get("first_initialization") is True and cert.get("prior_baseline") is None,
        "Not a first initialization certificate",
    )
    return score
