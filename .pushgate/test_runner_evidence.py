"""Regression checks for stale and partial campaign evidence."""

import json
import runpy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RUNNER = Path(__file__).resolve().with_name("run.py")


class RunnerEvidenceTests(unittest.TestCase):
    def run_campaign(self, *, partial_xml=False, timeout=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / ".pushgate/reports/test-sha"
            folder.mkdir(parents=True)
            xml = folder / "backend.xml"
            xml.write_text('<testsuite><testcase name="stale-pass"/></testsuite>')
            for name in (
                "backend.coverage",
                "backend-coverage.json",
                "backend-coverage-check.json",
            ):
                (folder / name).write_text("stale evidence")

            def execute(command, **kwargs):
                if "pytest" in command:
                    self.assertFalse(xml.exists())
                    self.assertFalse((folder / "backend.coverage").exists())
                    self.assertFalse((folder / "backend-coverage.json").exists())
                    self.assertFalse((folder / "backend-coverage-check.json").exists())
                    if partial_xml:
                        xml.write_text(
                            '<testsuite><testcase name="partial-pass"/></testsuite>'
                        )
                    if timeout:
                        raise subprocess.TimeoutExpired(command, 600)
                    return subprocess.CompletedProcess(command, 1)
                if ".pushgate/score.py" in command:
                    return subprocess.CompletedProcess(command, 1)
                return subprocess.CompletedProcess(command, 0)

            with (
                patch("pathlib.Path.cwd", return_value=root),
                patch("subprocess.check_output", return_value="test-sha"),
                patch("subprocess.run", side_effect=execute),
                self.assertRaises(SystemExit) as outcome,
            ):
                runpy.run_path(str(RUNNER), run_name="__main__")
            self.assertEqual(outcome.exception.code, 1)
            return json.loads((folder / "report.json").read_text())

    def test_failed_backend_cannot_reuse_old_passing_junit(self):
        report = self.run_campaign()
        rows = {row["id"]: row for row in report["tests"]}
        self.assertNotIn("stale-pass", rows)
        self.assertEqual(rows["stage-backend"]["status"], "fail")

    def test_partial_passing_junit_does_not_hide_process_failure(self):
        report = self.run_campaign(partial_xml=True)
        rows = {row["id"]: row for row in report["tests"]}
        self.assertEqual(rows["partial-pass"]["status"], "pass")
        self.assertEqual(rows["stage-backend"]["status"], "fail")
        self.assertTrue(report["missing_evidence"])

    def test_partial_junit_does_not_hide_timeout(self):
        report = self.run_campaign(partial_xml=True, timeout=True)
        rows = {row["id"]: row for row in report["tests"]}
        self.assertEqual(rows["stage-backend"]["status"], "notrun")


if __name__ == "__main__":
    unittest.main()
