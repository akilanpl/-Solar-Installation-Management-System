"""Preflight Chromium before preparing the explicitly disposable browser database.

Run from any directory. Never resets a database if browser startup is blocked.
The maintained QA runner starts owned API/Next processes through Playwright.
"""
import argparse
import os
import socket
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "apps/api"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    values = dotenv_values(args.env, interpolate=False)
    environment = {**os.environ, **{key: value for key, value in values.items() if value is not None}}
    sys.path.insert(0, str(API))
    # Set both values before importing the existing safety guard.
    os.environ.update({key: value for key, value in environment.items() if key.startswith("SOLAROPS_")})
    from tests.conftest import TEST_DATABASE_URL, _assert_safe

    _assert_safe(TEST_DATABASE_URL)
    for port in (3001, 8001):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind(("127.0.0.1", port))
            except OSError:
                parser.error(f"QA port {port} is occupied; existing service preserved")
    probe = """const {chromium}=require('@playwright/test');
(async()=>{let browser;try{browser=await chromium.launch({headless:true,chromiumSandbox:true});
const page=await browser.newPage();await page.goto('about:blank');console.log('Chromium preflight PASS');
}catch(error){console.error(error.message);process.exitCode=1;}finally{if(browser)await browser.close();}})();"""
    try:
        result = subprocess.run(["node", "-e", probe], cwd=ROOT / "apps/web", env=environment, timeout=30)
    except subprocess.TimeoutExpired:
        print("BLOCKED: Chromium preflight timed out; database untouched.", file=sys.stderr)
        return 2
    if result.returncode:
        print("BLOCKED: Chromium preflight failed; database untouched. No security settings changed.", file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, "scripts/run_browser_qa.py"], cwd=API, env=environment)


if __name__ == "__main__":
    sys.exit(main())
