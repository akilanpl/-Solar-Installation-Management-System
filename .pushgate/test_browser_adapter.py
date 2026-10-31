"""The checked-in adapter must resolve and execute the installed real CLI."""
import subprocess
import unittest
from pathlib import Path


class BrowserAdapterTests(unittest.TestCase):
    def test_installed_playwright_cli_is_export_safe_and_executable(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["node", "-e", ("const {spawnSync}=require('node:child_process');"
             "const a=require('./.pushgate/campaigns/browser_campaign.cjs');"
             "const r=spawnSync(process.execPath,[a.resolveCli(),'--version'],{encoding:'utf8'});"
             "process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');"
             "process.exit(r.status===null?1:r.status);")],
            cwd=root, capture_output=True, text=True, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"Version 1\.[0-9]+\.[0-9]+")
