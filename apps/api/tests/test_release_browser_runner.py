"""A browser environment failure must not trigger destructive fixture preparation."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "release_browser_runner", Path(__file__).resolve().parents[1] / "scripts/run_release_browser.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


@pytest.mark.parametrize("timeout", [False, True])
def test_browser_preflight_failure_never_prepares_database(monkeypatch, tmp_path, timeout):
    env = tmp_path / "private.env"
    env.write_text("")
    monkeypatch.setattr(sys, "argv", ["run_release_browser", "--env", str(env)])

    def probe(*args, **kwargs):
        if timeout:
            raise subprocess.TimeoutExpired("node", 30)
        return subprocess.CompletedProcess("node", 1)

    monkeypatch.setattr(runner.subprocess, "run", probe)
    monkeypatch.setattr(runner.subprocess, "call", lambda *_args, **_kwargs: pytest.fail("Prepared browser fixtures after launch failure"))
    assert runner.main() == 2
