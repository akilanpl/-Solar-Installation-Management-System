"""Mutation engine integrity: no runtime/collection/timeout credit or silent drops."""

import runpy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = runpy.run_path(str(ROOT / ".pushgate/campaigns/mutation_campaign.py"))


class MutationEngineTests(unittest.TestCase):
    def classify(self, xml, code=1, timeout=False):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.xml"
            path.write_text(xml)
            return ENGINE["classify_junit"](path, code, timeout=timeout)

    def test_assertion_failure_is_killed_only_with_test_failure_exit(self):
        xml = '<testsuite tests="1"><testcase name="guard"><failure message="AssertionError: expected denied"/></testcase></testsuite>'
        self.assertEqual(self.classify(xml), ("killed", 1))
        self.assertEqual(self.classify(xml, code=2), ("error", 1))
        self.assertEqual(self.classify(xml, timeout=True), ("timeout", 0))

    def test_runtime_setup_skipped_empty_and_partial_output_cannot_be_kills(self):
        for xml in (
            '<testsuite tests="1"><testcase name="guard"><failure message="TypeError: wrong type">trace includes assert expected</failure></testcase></testsuite>',
            '<testsuite tests="1"><testcase name="guard"><error message="database down"/></testcase></testsuite>',
            '<testsuite tests="1"><testcase name="guard"><skipped/></testcase></testsuite>',
            '<testsuite tests="2"><testcase name="partial"/></testsuite>',
            '<testsuite tests="0"/>', '<testsuite',
        ):
            with self.subTest(xml=xml):
                self.assertEqual(self.classify(xml)[0], "error")

    def test_passing_tests_are_survived_not_killed(self):
        self.assertEqual(self.classify('<testsuite tests="1"><testcase name="guard"/></testsuite>', code=0), ("survived", 1))

    def test_mutation_requires_exact_single_function_expression(self):
        original = 'def guard():\n    return value != expected\n\ndef other():\n    return value != expected\n'
        mutant, line = ENGINE["mutate"](original, "guard", "value != expected", "False")
        self.assertEqual(line, 2)
        self.assertEqual(mutant.count("value != expected"), 1)
        self.assertIn('def other():\n    return value != expected', mutant)
        for function, before in (("missing", "value != expected"), ("guard", "missing")):
            with self.assertRaises(ValueError):
                ENGINE["mutate"](original, function, before, "False")

    def test_full_reviewed_inventory_applies_to_current_source(self):
        inventory = ENGINE["INVENTORY"]
        self.assertEqual(len(inventory), 17)
        self.assertEqual(len({row[0] for row in inventory}), 17)
        for identity, filename, function, before, after, test in inventory:
            with self.subTest(mutant=identity):
                original = (ROOT / "apps/api/app" / filename).read_text()
                mutated, line = ENGINE["mutate"](original, function, before, after)
                self.assertNotEqual(original, mutated)
                self.assertGreater(line, 0)
                self.assertTrue((ROOT / "apps/api/tests" / test.split("::")[0]).is_file())


if __name__ == "__main__":
    unittest.main()
