"""Changed coverage cannot receive credit from comments, old code or missing modules."""

import unittest

from check_diff_coverage import changed_lines, evaluate


class DiffCoverageTests(unittest.TestCase):
    def test_unified_hunks_respect_insertions_and_deletions(self):
        diff = (
            "+++ b/apps/api/app/main.py\n@@ -1 +1,2 @@\n+x\n+y\n@@ -8,2 +9,0 @@\n-x\n-y"
        )
        self.assertEqual(changed_lines(diff), {"apps/api/app/main.py": {1, 2}})

    def test_only_changed_executable_lines_count(self):
        row = evaluate(
            {"apps/api/app/main.py": {1, 2, 3}},
            {
                "files": {
                    "app\\main.py": {
                        "executed_lines": [1, 10],
                        "missing_lines": [2, 11],
                    }
                }
            },
            90,
        )
        self.assertEqual((row["covered"], row["total"], row["status"]), (1, 2, "fail"))

    def test_new_unimported_module_fails(self):
        row = evaluate({"apps/api/app/new.py": {1}}, {"files": {}}, 90)
        self.assertEqual(row["status"], "fail")
        self.assertEqual(row["unmeasured_files"], ["apps/api/app/new.py"])

    def test_exact_threshold_and_no_app_changes(self):
        row = evaluate(
            {"apps/api/app/main.py": set(range(1, 11))},
            {
                "files": {
                    "app/main.py": {
                        "executed_lines": list(range(1, 10)),
                        "missing_lines": [10],
                    }
                }
            },
            90,
        )
        self.assertEqual(row["status"], "pass")
        self.assertEqual(evaluate({}, {"files": {}}, 90)["total"], 0)

    def test_invalid_thresholds_fail_closed(self):
        for threshold in (True, -1, 101, float("nan")):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                evaluate({}, {"files": {}}, threshold)


if __name__ == "__main__":
    unittest.main()
