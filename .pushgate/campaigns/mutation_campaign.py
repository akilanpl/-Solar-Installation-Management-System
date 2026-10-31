"""Bounded critical-guard mutation spot-check using real isolated PostgreSQL.

This deliberately limited inventory is not an exhaustive mutation score.
The campaign uses an isolated Git clone restored between mutants. Each mutation
runs against a newly created, uniquely named PostgreSQL database owned by this invocation. No input result/command is trusted.
"""

import argparse
import ast
import difflib
import json
import os
import secrets
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# id, source, function, exact expression, replacement, existing regression test
INVENTORY = [
    ("utc-session", "db/session.py", "_set_utc", "SET TIME ZONE 'UTC'", "SET TIME ZONE 'Asia/Kolkata'", "test_transaction_response.py::test_pool_rollback_keeps_utc_session_timezone"),
    ("commit-omitted", "db/session.py", "get_db", "session.commit()", "session.flush()", "test_transaction_response.py::test_login_session_is_committed_when_response_headers_are_sent"),
    ("rollback-omitted", "db/session.py", "get_db", "session.rollback()", "pass", "test_transaction_response.py::test_failed_commit_cannot_emit_success_or_usable_session_cookie"),
    ("warranty-void", "services/warranty_service.py", "evaluate_coverage", 'if coverage.status == "void":', "if False:", "test_phase4b_warranty.py::test_same_day_expiry_and_void_invalidate_cached_coverage"),
    ("warranty-expiry", "services/warranty_service.py", "evaluate_coverage", "if at > _as_utc(coverage.ends_at):", "if at >= _as_utc(coverage.ends_at):", "test_phase4b_warranty.py::test_expiration_boundary_and_policy_snapshot_preserved"),
    ("extension-replay", "services/warranty_extension_service.py", "request_extension", "if duplicate is not None:", "if False:", "test_phase4e_warranty.py::test_duplicate_request_is_idempotent"),
    ("invoice-authorization", "services/inventory_service.py", "consume_service_invoice_stock", "if user.role_code not in WAREHOUSE:", "if False:", "test_service_consumption_guards.py::test_missing_invoice_and_nonwarehouse_command_never_write_stock"),
    ("invoice-version", "services/inventory_service.py", "consume_service_invoice_stock", "estimate.version != invoice.estimate_version", "False", "test_service_consumption_guards.py::test_persisted_invoice_source_guard_rejects_without_stock_writes"),
    ("invoice-snapshot", "services/inventory_service.py", "consume_service_invoice_stock", "invoice.lines != estimate.lines", "False", "test_service_consumption_guards.py::test_persisted_invoice_source_guard_rejects_without_stock_writes"),
    ("invoice-quantity-type", "services/inventory_service.py", "consume_service_invoice_stock", "type(quantity) is not int", "not isinstance(quantity, int)", "test_service_consumption_guards.py::test_invalid_legacy_parts_never_create_partial_consumption"),
    ("invoice-serialization", "services/inventory_service.py", "consume_service_invoice_stock", "if component.requires_serial_tracking:", "if False:", "test_service_consumption_guards.py::test_invalid_legacy_parts_never_create_partial_consumption"),
    ("outbox-content", "services/syscache_service.py", "emit_invalidation", "existing.aggregate_id != aggregate_id", "False", "test_finance_syscache_integration.py::test_duplicate_outbox_event_preserves_callers_transaction"),
    ("outbox-duplicate-receipt", "services/syscache_service.py", "emit_invalidation", "return existing", "return event", "test_finance_syscache_integration.py::test_duplicate_outbox_event_preserves_callers_transaction"),
    ("offline-assignment", "services/offline_sync_service.py", "_check_survey_access", "survey.assigned_technician_user_id != user.id", "False", "test_phase4e_offline.py::test_offline_user_isolation_and_assignment_scope"),
    ("offline-version", "services/offline_sync_service.py", "_check_survey_version", "if int(base) != survey.field_version:", "if False:", "test_phase4e_offline.py::test_offline_stale_version_conflicts_without_overwrite"),
    ("mfa-attempt-durability", "services/mfa_service.py", "_register_failure", "factor.attempt_count += 1", "factor.attempt_count += 0", "test_phase4e_auth.py::test_totp_lockout_after_repeated_failures"),
    ("offline-evidence-retry", "services/offline_sync_service.py", "upload_evidence", 'existing.result.get("content_sha256") != digest', "False", "test_phase4e_offline.py::test_offline_evidence_rejects_tampered_retry"),
]


def mutate(source, function, before, after):
    """Replace exactly one verified expression inside exactly one AST function."""
    tree = ast.parse(source)
    functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function]
    if len(functions) != 1:
        raise ValueError("Mutation function is missing or ambiguous")
    node = functions[0]
    lines = source.splitlines(keepends=True)
    start, end = sum(map(len, lines[:node.lineno - 1])), sum(map(len, lines[:node.end_lineno]))
    body = source[start:end]
    if body.count(before) != 1:
        raise ValueError("Mutation expression is missing or ambiguous")
    position = start + body.index(before)
    mutated = source[:position] + after + source[position + len(before):]
    ast.parse(mutated)
    return mutated, source[:position].count("\n") + 1


def classify_junit(path, returncode, *, timeout=False):
    if timeout:
        return "timeout", 0
    try:
        tree = ET.parse(path)
        cases = list(tree.iter("testcase"))
        suites = [node for node in tree.iter("testsuite") if not node.findall("testsuite")]
        declared = sum(int(node.get("tests", str(len(list(node.iter("testcase")))))) for node in suites)
        if declared != len(cases):
            return "error", len(cases)
        if not cases or any(case.find("error") is not None or case.find("skipped") is not None for case in cases):
            return "error", len(cases)
        failures = [case.find("failure") for case in cases if case.find("failure") is not None]
        if returncode == 0 and not failures:
            return "survived", len(cases)
        if returncode == 1 and failures:
            # Setup/runtime exceptions are not proof that the regression killed
            # a mutant. Credit only observable assertion/expectation failures.
            messages = [failure.get("message", "").lstrip() for failure in failures]
            if all(msg.startswith("AssertionError") or msg.startswith("Failed: DID NOT RAISE")
                   for msg in messages):
                return "killed", len(cases)
        return "error", len(cases)
    except (OSError, ET.ParseError, ValueError):
        return "error", 0


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def run_tests(checkout, tests, evidence, label, database_url):
    """Create and later drop only an exclusively owned fresh database."""
    import psycopg
    from psycopg import sql
    from sqlalchemy.engine import make_url

    original = make_url(database_url)
    admin_url = original.set(drivername="postgresql", database="postgres")
    # Eight digits satisfy the test fixture's explicit disposable allowlist.
    name = f"solarops_release_test_{secrets.randbelow(100000000):08d}"
    test_url = original.set(database=name)
    xml = evidence / f"{label}.xml"
    log = evidence / f"{label}.log"
    created = False
    try:
        with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as admin:
            # CREATE must fail if a name is already owned elsewhere. Never
            # drop/replace an existing database to make room for this campaign.
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            created = True
        env = dict(os.environ,
            SOLAROPS_TEST_DATABASE_URL=test_url.render_as_string(hide_password=False),
            SOLAROPS_DATABASE_URL=test_url.render_as_string(hide_password=False),
            SOLAROPS_DISPOSABLE_TEST_DATABASE_NAME=name, PYTHONDONTWRITEBYTECODE="1")
        command = [sys.executable, "-m", "pytest", *[f"tests/{test}" for test in tests],
                   "-q", f"--junitxml={xml}"]
        timed_out = False
        with log.open("w") as output:
            try:
                result = subprocess.run(command, cwd=checkout / "apps/api", env=env,
                    stdout=output, stderr=subprocess.STDOUT, timeout=120, check=False)
                code = result.returncode
            except subprocess.TimeoutExpired:
                timed_out, code = True, None
        status, count = classify_junit(xml, code, timeout=timed_out)
        return {"status": status, "test_count": count, "junit": str(xml), "log": str(log), "database": name}
    finally:
        if created:
            with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as admin:
                admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def write_junit(path, report):
    suite = ET.Element("testsuite", name="scoped-guard-mutation", tests=str(report["planned"]))
    for row in report["mutants"]:
        case = ET.SubElement(suite, "testcase", name=row["id"])
        if row["status"] in {"error", "timeout", "unrun"}:
            ET.SubElement(case, "error", message=row["status"])
    # Surviving mutants are honest measurement, not failed assertions. The
    # threshold is an additional explicit campaign assertion.
    suite.set("tests", str(report["planned"] + 1))
    gate = ET.SubElement(suite, "testcase", name="scoped-kill-rate-at-least-60-percent")
    if report["decision"] != "PASS":
        ET.SubElement(gate, "failure", message="Incomplete campaign or scoped kill rate below 60%")
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--junit", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    sha = git(root, "rev-parse", "HEAD")
    dirty = git(root, "status", "--porcelain", "--untracked-files=all")
    evidence = output.parent / f"mutation-{secrets.token_hex(6)}"
    evidence.mkdir()
    report = {"schema_version": 1, "sha": sha, "scope": "critical-guard-spotcheck",
              "inventory": [row[0] for row in INVENTORY], "planned": len(INVENTORY),
              "baseline": {"status": "error", "tests": 0}, "mutants": [],
              "decision": "FAIL", "errors": 0, "killed": 0, "kill_percent": 0.0}
    originals = {}
    applicable = True
    for identity, filename, function, before, after, test in INVENTORY:
        row = {"id": identity, "status": "unrun", "file": f"apps/api/app/{filename}",
               "line": None, "operator": {"before": before, "after": after},
               "test": test, "test_count": 0}
        report["mutants"].append(row)
        try:
            source = (root / row["file"]).read_text()
            mutated, row["line"] = mutate(source, function, before, after)
            originals[identity] = (source, mutated)
        except (OSError, ValueError, SyntaxError):
            row["status"], applicable = "error", False
    try:
        if dirty or not applicable:
            raise ValueError("Dirty source or fixed mutation inventory not applicable")
        database_url = os.environ["SOLAROPS_TEST_DATABASE_URL"]
        with tempfile.TemporaryDirectory(prefix="solarops-mutation-") as temporary:
            checkout = Path(temporary) / "source"
            subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(root), str(checkout)], check=True)
            if git(checkout, "rev-parse", "HEAD") != sha:
                raise ValueError("Clone source SHA mismatch")
            baseline = run_tests(checkout, sorted({row[-1] for row in INVENTORY}), evidence, "baseline", database_url)
            report["baseline"] = {**baseline, "status": "passed" if baseline["status"] == "survived" else "error", "tests": baseline["test_count"]}
            if report["baseline"]["status"] != "passed":
                raise ValueError("Unmodified selected regression baseline failed")
            for row in report["mutants"]:
                target = checkout / row["file"]
                original, mutated = originals[row["id"]]
                target.write_text(mutated)
                (evidence / f"{row['id']}.diff").write_text("".join(difflib.unified_diff(
                    original.splitlines(True), mutated.splitlines(True), fromfile=row["file"], tofile=row["file"])))
                try:
                    row.update(run_tests(checkout, [row["test"]], evidence, row["id"], database_url))
                except Exception as exc:  # noqa: BLE001 - record infrastructure errors without counting kills
                    row.update(status="error", error=type(exc).__name__)
                finally:
                    target.write_text(original)
        if git(root, "rev-parse", "HEAD") != sha or git(root, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("Original source changed during mutation campaign")
    except Exception as exc:  # noqa: BLE001 - record infrastructure errors without counting kills
        report["campaign_error"] = type(exc).__name__
    report["killed"] = sum(row["status"] == "killed" for row in report["mutants"])
    report["errors"] = sum(row["status"] in {"error", "timeout", "unrun"} for row in report["mutants"])
    report["kill_percent"] = report["killed"] / report["planned"] * 100
    if not report.get("campaign_error") and report["baseline"]["status"] == "passed" and not report["errors"] and report["kill_percent"] >= 60:
        report["decision"] = "PASS"
    output.write_text(json.dumps(report, indent=2) + "\n")
    if args.junit:
        write_junit(args.junit, report)
    print(f"Scoped guard mutation: {report['decision']}; {report['killed']}/{report['planned']} killed; {report['errors']} errors/unrun")
    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
