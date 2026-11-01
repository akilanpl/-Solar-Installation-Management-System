"""Invalid browser targets must fail before importing/resetting database fixtures."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "apps/api/scripts/run_ci_browser.py"


class BrowserSafetyTests(unittest.TestCase):
    def test_reset_requires_explicit_local_test_target_and_acknowledgment(self):
        for target, arguments in (
            (None, ["--reset-test-db"]),
            ("postgresql+psycopg://localhost/solarops_dev", ["--reset-test-db"]),
            ("postgresql+psycopg://remote.invalid/solarops_test", ["--reset-test-db"]),
            ("postgresql+psycopg://localhost/solarops_test", []),
        ):
            with self.subTest(target=target, arguments=arguments):
                environment = os.environ.copy()
                environment.pop("SOLAROPS_TEST_DATABASE_URL", None)
                if target:
                    environment["SOLAROPS_TEST_DATABASE_URL"] = target
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), *arguments],
                    check=False,
                    cwd=ROOT,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("alembic.runtime.migration", result.stderr)


if __name__ == "__main__":
    unittest.main()
