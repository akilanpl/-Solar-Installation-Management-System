"""Exercise actual child commands and JUnit collection against a real Git tree."""

import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RUNNER = runpy.run_path(str(Path(__file__).with_name("run.py")))


class CampaignExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder = self.root / ".pushgate/reports/test"
        self.folder.mkdir(parents=True)
        (self.root / ".gitignore").write_text(".pushgate/reports/\n")
        (self.root / "source.py").write_text("original\n")
        for command in (
            ["git", "init", "-q"], ["git", "add", "."],
            ["git", "-c", "user.name=Gate Test", "-c", "user.email=gate@example.invalid",
             "commit", "-qm", "test fixture"],
        ):
            subprocess.run(command, cwd=self.root, check=True, capture_output=True)

    def run_child(self, program, **kwargs):
        return RUNNER["run_stage"](
            self.root, self.folder, "example", "E04", "P0", ".",
            [sys.executable, "-c", program, str(self.folder / "example.xml")],
            require_junit=True, **kwargs,
        )

    def write_xml(self, xml):
        return f"from pathlib import Path; import sys; Path(sys.argv[1]).write_text({xml!r}); "

    def test_actual_success_command_and_fresh_junit_pass(self):
        rows = self.run_child(self.write_xml(
            '<testsuite tests="1"><testcase name="durable-record"/></testsuite>'))
        self.assertEqual([row["status"] for row in rows], ["pass", "pass"])
        self.assertRegex(rows[0]["sha"], r"^[0-9a-f]{40}$")
        self.assertIn("durable-record", (self.folder / "example.xml").read_text())

    def test_nonzero_exit_cannot_hide_behind_partial_pass(self):
        rows = self.run_child(self.write_xml(
            '<testsuite><testcase name="first-case"/></testsuite>') + "sys.exit(3)")
        self.assertEqual(rows[0]["status"], "fail")
        self.assertEqual(rows[1]["status"], "pass")
        self.assertIn("3", rows[0]["reason"])

    def test_success_without_junit_cannot_reuse_previous_output(self):
        xml = self.folder / "example.xml"
        xml.write_text('<testsuite><testcase name="stale"/></testsuite>')
        (self.folder / "example.log").write_text("stale log")
        rows = self.run_child("pass")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "fail")
        self.assertFalse(xml.exists())
        self.assertNotIn("stale log", (self.folder / "example.log").read_text())

    def test_truncated_or_skipped_junit_blocks_campaign(self):
        for xml in (
            '<testsuite tests="2"><testcase name="only-one"/></testsuite>',
            '<testsuite><testcase name="skipped"><skipped/></testcase></testsuite>',
            '<testsuite tests="0"/>', '<testsuite',
        ):
            with self.subTest(xml=xml):
                rows = self.run_child(self.write_xml(xml))
                self.assertEqual(rows[0]["status"], "fail")

    def test_timeout_is_notrun_even_when_partial_junit_exists(self):
        rows = self.run_child(self.write_xml(
            '<testsuite><testcase name="partial"/></testsuite>') +
            "import time; time.sleep(2)", timeout=0.1)
        self.assertEqual(rows[0]["status"], "notrun")
        self.assertEqual(rows[1]["status"], "pass")

    def test_source_mutation_invalidates_success(self):
        rows = self.run_child(self.write_xml(
            '<testsuite><testcase name="case"/></testsuite>') +
            "Path('source.py').write_text('changed')")
        self.assertEqual(rows[0]["status"], "fail")
        self.assertIn("Source changed", rows[0]["reason"])

    def test_missing_campaign_adapter_stays_notrun_and_removes_stale_xml(self):
        xml = self.folder / "example.xml"
        xml.write_text('<testsuite><testcase name="stale"/></testsuite>')
        rows = self.run_child("raise AssertionError('must not execute')",
                              prerequisites=("missing-dedicated-campaign.py",))
        self.assertEqual(rows[0]["status"], "notrun")
        self.assertFalse(xml.exists())
        self.assertIn("missing-dedicated-campaign.py", rows[0]["reason"])

    def test_mandatory_registry_has_fixed_executable_named_adapters(self):
        campaigns = RUNNER["mandatory_campaigns"](self.root, self.folder, sys.executable)
        names = {entry[0] for entry in campaigns}
        self.assertIn("outgoing-secret-history", names)
        self.assertIn("main-ratchet-two-order-ci", names)
        self.assertIn("customer-warranty-browser", names)
        self.assertIn("migration-preservation", names)
        self.assertEqual(len(names), len(campaigns))
        self.assertTrue(all(entry[4] and entry[5] for entry in campaigns))


if __name__ == "__main__":
    unittest.main()
