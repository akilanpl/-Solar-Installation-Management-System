"""Mutation adapter validator negative-path tests; not release mutation evidence."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

FILE = Path(__file__).parent / "campaigns/coverage_quality.py"
SPEC = importlib.util.spec_from_file_location("mutation_coverage_adapter", FILE)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)
SHA = "a" * 40


def synthetic_report(killed=12):
    """Unit fixture only; no JUnit/acceptance artifact is created from this."""
    ids = [f"unit-guard-{index}" for index in range(17)]
    return {
        "schema_version": 1,
        "sha": SHA,
        "scope": "critical-guard-spotcheck",
        "inventory": ids,
        "planned": 17,
        "baseline": {"status": "passed", "tests": 8},
        "mutants": [
            {"id": value, "status": "killed" if index < killed else "survived"}
            for index, value in enumerate(ids)
        ],
        "killed": killed,
        "kill_percent": killed / 17 * 100,
        "errors": 0,
        "decision": "PASS" if killed / 17 >= 0.6 else "FAIL",
    }


class MutationAdapterTests(unittest.TestCase):
    def test_recomputes_actual_score_for_explicit_bounded_scope(self):
        verified = ADAPTER.validate_mutation_report(synthetic_report(), SHA)
        self.assertEqual(verified["scope"], "critical-guard-spotcheck")
        self.assertEqual(verified["killed"], 12)
        self.assertAlmostEqual(verified["kill_percent"], 1200 / 17)

    def test_missing_duplicate_incomplete_or_foreign_inventory_fails(self):
        for change in (
            lambda r: r.update(sha="b" * 40),
            lambda r: r["mutants"].pop(),
            lambda r: r["inventory"].append("extra"),
            lambda r: r["mutants"][0].update(id=r["mutants"][1]["id"]),
        ):
            with self.subTest(change=change):
                report = synthetic_report()
                change(report)
                with self.assertRaises(ValueError):
                    ADAPTER.validate_mutation_report(report, SHA)

    def test_error_timeout_unrun_and_unknown_status_are_failures(self):
        for status in ("error", "timeout", "unrun", "skipped", "passed"):
            with self.subTest(status=status):
                report = synthetic_report()
                report["mutants"][0]["status"] = status
                with self.assertRaises(ValueError):
                    ADAPTER.validate_mutation_report(report, SHA)

    def test_fake_total_bad_baseline_and_below_threshold_fail(self):
        bad_percentage = synthetic_report()
        bad_percentage["kill_percent"] = 100
        bad_total = synthetic_report()
        bad_total["killed"] = 17
        bad_errors = synthetic_report()
        bad_errors["errors"] = 1
        for report in (synthetic_report(10), bad_percentage, bad_total, bad_errors):
            with self.assertRaises(ValueError):
                ADAPTER.validate_mutation_report(report, SHA)
        for baseline in (
            {"status": "error", "tests": 8},
            {"status": "passed", "tests": 0},
        ):
            report = synthetic_report()
            report["baseline"] = baseline
            with self.assertRaises(ValueError):
                ADAPTER.validate_mutation_report(report, SHA)

    def test_external_existing_report_is_deleted_before_fixed_engine_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "reports"
            folder.mkdir()
            script = root / ".pushgate/campaigns/mutation_campaign.py"
            script.parent.mkdir(parents=True)
            script.write_text("# unit fixture placeholder")
            output = folder / "mutation-report.json"
            output.write_text(json.dumps(synthetic_report()))

            def no_report(command, **kwargs):
                self.assertFalse(
                    output.exists(), "stale external report must be removed first"
                )
                self.assertEqual(command[1:], [str(script), "--output", str(output)])
                return subprocess.CompletedProcess(command, 0)

            with (
                patch.object(ADAPTER.subprocess, "run", side_effect=no_report),
                self.assertRaisesRegex(ValueError, "fresh report"),
            ):
                ADAPTER.execute_mutation_campaign(root, folder, SHA)


if __name__ == "__main__":
    unittest.main()
