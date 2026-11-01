"""Gate regressions: incomplete/low coverage must never become a PASS."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from check_backend_coverage import evaluate

ROOT = Path(__file__).resolve().parent


class BackendCoverageTests(unittest.TestCase):
    def setUp(self):
        self.config = {"coverage": {"line": 80, "branch": 70}}
        self.report = {
            "meta": {"branch_coverage": True},
            "files": {"app/main.py": {}},
            "totals": {
                "covered_lines": 80,
                "num_statements": 100,
                "covered_branches": 70,
                "num_branches": 100,
            },
        }

    def test_exact_thresholds_pass(self):
        self.assertEqual(
            [row["status"] for row in evaluate(self.report, self.config)],
            ["pass", "pass"],
        )

    def test_line_and_branch_are_independent(self):
        for key, expected in (
            ("covered_lines", ["fail", "pass"]),
            ("covered_branches", ["pass", "fail"]),
        ):
            with self.subTest(key=key):
                report = copy.deepcopy(self.report)
                report["totals"][key] -= 1
                self.assertEqual(
                    [row["status"] for row in evaluate(report, self.config)], expected
                )

    def test_rounding_cannot_hide_below_threshold(self):
        self.report["totals"].update(covered_lines=799999, num_statements=1000000)
        self.assertEqual(evaluate(self.report, self.config)[0]["status"], "fail")

    def test_configured_threshold_is_used(self):
        self.config["coverage"]["branch"] = 71
        self.assertEqual(evaluate(self.report, self.config)[1]["status"], "fail")

    def test_missing_branch_data_or_empty_source_is_rejected(self):
        for change in ({"meta": {"branch_coverage": False}}, {"files": {}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluate({**self.report, **change}, self.config)

    def test_invalid_counts_and_thresholds_are_rejected(self):
        for total, covered in ((0, 0), (100, -1), (100, 101), (True, 1), (100, "80")):
            with (
                self.subTest(total=total, covered=covered),
                self.assertRaises(ValueError),
            ):
                report = copy.deepcopy(self.report)
                report["totals"].update(num_statements=total, covered_lines=covered)
                evaluate(report, self.config)
        for threshold in (-1, 101, "80", True, float("nan")):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                evaluate(self.report, {"coverage": {"line": threshold, "branch": 70}})

    def test_cli_missing_and_malformed_evidence_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            config = folder / "config.yml"
            config.write_text("coverage: { line: 80, branch: 70 }", encoding="utf-8")
            evidence = folder / "coverage.json"
            output = folder / "result.json"
            for content in (None, "malformed-private-value", "{}"):
                if content is not None:
                    evidence.write_text(content, encoding="utf-8")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "check_backend_coverage.py"),
                        "--config",
                        str(config),
                        "--coverage",
                        str(evidence),
                        "--output",
                        str(output),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 1)
                self.assertNotIn(
                    "malformed-private-value", result.stdout + result.stderr
                )
                rows = json.loads(output.read_text(encoding="utf-8"))["tests"]
                self.assertEqual(rows[0]["status"], "notrun")


if __name__ == "__main__":
    unittest.main()
