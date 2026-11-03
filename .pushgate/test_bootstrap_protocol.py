"""Adversarial protocol tests; synthetic fixtures never become release evidence."""

import copy
import io
import json
import unittest
import zipfile

from bootstrap_protocol import *


class BootstrapTrustTests(unittest.TestCase):
    def setUp(self):
        self.pins = {PIN_MAIN: "a" * 40, PIN_CONTROLLER: "b" * 40}
        self.run = {
            "id": 1,
            "run_attempt": 1,
            "repository": {"full_name": REPOSITORY, "id": REPOSITORY_ID},
            "path": WORKFLOW,
            "event": "push",
            "head_branch": CONTROL_REF[11:],
            "head_sha": "b" * 40,
            "actor": {"login": "akilanpl"},
            "triggering_actor": {"login": "akilanpl"},
        }
        self.context = {
            "GITHUB_ACTIONS": "true",
            "CI": "true",
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REF": CONTROL_REF,
            "GITHUB_SHA": "b" * 40,
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        self.main = {"sha": "a" * 40, "dirty": False}
        self.controller = {"sha": "b" * 40, "dirty": False}

    def verify(self, **changes):
        args = {
            "context": self.context,
            "pins": self.pins,
            "run": self.run,
            "main_state": self.main,
            "controller_state": self.controller,
            "live_main": "a" * 40,
            "history": [],
        }
        args.update(changes)
        return validate_identity(**args)

    def test_first_initialization_identity(self):
        self.assertEqual(self.verify(), ("a" * 40, "b" * 40))

    def test_repeated_initialization(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.verify(history=[123])

    def test_wrong_sha_dirty_main_and_controller(self):
        for changes in [
            {"live_main": "c" * 40},
            {"main_state": {"sha": "a" * 40, "dirty": True}},
            {"controller_state": {"sha": "c" * 40, "dirty": False}},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.verify(**changes)

    def test_pr_fork_actor_attempt_and_workflow_cannot_impersonate_main(self):
        for key, value in [
            ("event", "pull_request"),
            ("head_sha", "c" * 40),
            ("path", "evil.yml"),
            ("repository", {"id": 99, "full_name": REPOSITORY}),
            ("actor", {"login": "fork-user"}),
            ("run_attempt", 2),
        ]:
            run = copy.deepcopy(self.run)
            run[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(run=run)

    def test_missing_owner_pin(self):
        with self.assertRaises(ValueError):
            self.verify(pins={})

    def archive(self, names):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as z:
            for name, data in names:
                z.writestr(name, data)
        blob = output.getvalue()
        return blob, {"expired": False, "digest": "sha256:" + digest(blob)}

    def test_genuine_digest_and_altered_archive(self):
        blob, artifact = self.archive([("certificate.json", "{}")])
        self.assertEqual(validate_archive(blob, artifact), {"certificate.json": b"{}"})
        for changed in [blob + b"altered", blob[:-1]]:
            with self.assertRaises(ValueError):
                validate_archive(changed, artifact)
        artifact["expired"] = True
        with self.assertRaises(ValueError):
            validate_archive(blob, artifact)

    def test_duplicate_and_traversal_rejected(self):
        for names in [[("../escape", "x")], [("x", "a"), ("x", "b")]]:
            blob, artifact = self.archive(names)
            with self.assertRaises(ValueError):
                validate_archive(blob, artifact)

    def test_missing_certificate_never_certifies(self):
        with self.assertRaisesRegex(ValueError, "Certificate missing"):
            validate_certificate(
                {}, self.pins, self.run, {}, "a" * 40, lambda _: 100, []
            )

    def test_failed_or_incomplete_campaign_never_certifies(self):
        identity = {"sha": "a" * 40, "dirty": False}
        report = {
            "sha": "a" * 40,
            "source_start": identity,
            "source_end": identity,
            "decision": "PASS",
            "score": 100,
            "tests": [{"status": "fail", "sev": "P0", "family": "S01"}] * 100,
        }
        with self.assertRaises(ValueError):
            validate_rows(report, lambda _: 100)
        report["tests"] = [{"status": "pass", "sev": "P0", "family": "S01"}] * 100
        with self.assertRaises(ValueError):
            validate_rows(report, lambda _: 100)

    def test_score_regression_absolute_floor_and_valid_ratchet(self):
        check_ratchet(98, 100)
        for candidate, baseline in [(97.9, 100), (89, 90), (101, 100), (True, 100)]:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                check_ratchet(candidate, baseline)

    def certificate_fixture(self):
        import xml.etree.ElementTree as ET

        sha = "a" * 40
        identity = {"sha": sha, "dirty": False}
        stages = CAMPAIGNS | {
            "gate-selftest",
            "backend",
            "backend-coverage-export",
            "backend-coverage-check",
            "frontend",
            "typecheck",
            "lint-api",
            "lint-web",
            "build",
            "dependency-audit",
        }
        rows = [
            {"id": "stage-" + name, "family": "S01", "sev": "P0", "status": "pass"}
            for name in stages
        ]
        rows += [
            {"id": str(i), "family": family + "01", "sev": "P0", "status": "pass"}
            for i, family in enumerate(sorted(FAMILIES) * 8)
        ]
        report = {
            "sha": sha,
            "source_start": identity,
            "source_end": identity,
            "tests": rows,
            "missing_evidence": [],
            "score": 100,
            "decision": "PASS",
        }
        normal = [["tests.example", "test_" + str(i)] for i in range(100)]
        inventory = {
            "main_sha": sha,
            "source_files": ["100644 blob source\tapp.py"],
            "junit_cases": {
                "backend.xml": normal,
                "ci-reverse-order.xml": normal[::-1],
                "frontend.xml": [["web", "test"]],
                "core-browser.xml": [["core", "test"]],
            },
        }
        inventory["junit_cases"].update({c + ".xml": [[c, "test"]] for c in CAMPAIGNS})
        data = {
            "report.json": report,
            "inventory.json": inventory,
            "backend-coverage-check.json": {
                "tests": [
                    {
                        "id": "backend-" + kind + "-coverage",
                        "status": "pass",
                        "threshold": floor,
                        "covered": 100,
                        "total": 100,
                    }
                    for kind, floor in [("line", 80), ("branch", 70)]
                ]
            },
            "backend-coverage.json": {
                "meta": {"branch_coverage": True},
                "files": {"app.py": {}},
                "totals": {
                    "covered_lines": 100,
                    "num_statements": 100,
                    "covered_branches": 100,
                    "num_branches": 100,
                },
            },
            "diff-coverage-measured.json": {
                "sha": sha,
                "threshold": 90,
                "base_sha": sha,
                "covered": 0,
                "total": 0,
                "files": [],
                "percent": 100,
            },
            "candidate-secret-history.json": [],
            "core-database-verification.json": {"status": "PASS"},
            "mutation-report.json": {
                "sha": sha,
                "planned": 15,
                "errors": 0,
                "kill_percent": 100,
                "decision": "PASS",
                "killed": 15,
                "inventory": [str(i) for i in range(15)],
                "mutants": [{"id": str(i), "status": "killed"} for i in range(15)],
                "baseline": {"status": "passed", "tests": 1},
                "schema_version": 1,
                "scope": "critical-guard-spotcheck",
            },
        }
        files = {name: json.dumps(value).encode() for name, value in data.items()}
        for name, cases in inventory["junit_cases"].items():
            suite = ET.Element("testsuite", tests=str(len(cases)))
            for classname, case in cases:
                ET.SubElement(suite, "testcase", classname=classname, name=case)
            files[name] = ET.tostring(suite)
        cert = {
            "schema": 1,
            "kind": "first-accepted-main-baseline",
            "repository": REPOSITORY,
            "repository_id": REPOSITORY_ID,
            "main_sha": sha,
            "controller_sha": "b" * 40,
            "run_id": 1,
            "run_attempt": 1,
            "first_initialization": True,
            "prior_baseline": None,
            "files": {n: digest(b) for n, b in files.items()},
        }
        files["certificate.json"] = json.dumps(cert).encode()
        run = dict(self.run, status="completed", conclusion="success")
        artifact = {
            "workflow_run": {"id": 1, "head_sha": "b" * 40},
            "name": f"first-baseline-{sha}-attempt-1",
        }
        return files, run, artifact, inventory["source_files"]

    def test_complete_initial_certificate_is_accepted(self):
        files, run, artifact, source = self.certificate_fixture()
        self.assertEqual(
            validate_certificate(
                files, self.pins, run, artifact, "a" * 40, lambda _: 100, source
            ),
            100,
        )

    def test_certificate_negative_evidence_and_provenance(self):
        for failure in [
            "missing",
            "hash",
            "sha",
            "run",
            "pr",
            "coverage",
            "security",
            "inventory",
            "campaign",
        ]:
            files, run, artifact, source = self.certificate_fixture()
            if failure == "missing":
                del files["backend.xml"]
            elif failure == "hash":
                files["frontend.xml"] += b"changed"
            elif failure == "sha":
                source = ["wrong source"]
            elif failure == "run":
                artifact["workflow_run"]["id"] = 2
            elif failure == "pr":
                run["event"] = "pull_request"
            else:
                name = {
                    "coverage": "backend-coverage.json",
                    "security": "candidate-secret-history.json",
                    "inventory": "inventory.json",
                    "campaign": "report.json",
                }[failure]
                value = json.loads(files[name])
                if failure == "coverage":
                    value["totals"]["covered_branches"] = 0
                elif failure == "security":
                    value = [{"finding": "test"}]
                elif failure == "inventory":
                    del value["junit_cases"]["core-browser.xml"]
                else:
                    value["tests"][0]["status"] = "fail"
                files[name] = json.dumps(value).encode()
                cert = json.loads(files["certificate.json"])
                cert["files"][name] = digest(files[name])
                files["certificate.json"] = json.dumps(cert).encode()
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                validate_certificate(
                    files, self.pins, run, artifact, "a" * 40, lambda _: 100, source
                )

    def test_independent_review_integrity_regressions(self):
        for kind in [
            "diff-percent",
            "diff-inventory",
            "mutation-baseline",
            "missing-order",
            "missing-selftest",
        ]:
            files, run, artifact, source = self.certificate_fixture()
            if kind.startswith("diff"):
                name = "diff-coverage-measured.json"
                data = json.loads(files[name])
                data.update(covered=0, total=100, percent=100)
                if kind == "diff-inventory":
                    data.update(covered=100)
                files[name] = json.dumps(data).encode()
            elif kind == "mutation-baseline":
                name = "mutation-report.json"
                data = json.loads(files[name])
                data["baseline"]["tests"] = 0
                files[name] = json.dumps(data).encode()
            elif kind == "missing-order":
                name = "inventory.json"
                data = json.loads(files[name])
                del data["junit_cases"]["main-ratchet-two-order-ci.xml"]
                files[name] = json.dumps(data).encode()
            else:
                name = "report.json"
                data = json.loads(files[name])
                data["tests"] = [
                    r for r in data["tests"] if r["id"] != "stage-gate-selftest"
                ]
                files[name] = json.dumps(data).encode()
            cert = json.loads(files["certificate.json"])
            cert["files"][name] = digest(files[name])
            files["certificate.json"] = json.dumps(cert).encode()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_certificate(
                    files, self.pins, run, artifact, "a" * 40, lambda _: 100, source
                )


if __name__ == "__main__":
    unittest.main()
