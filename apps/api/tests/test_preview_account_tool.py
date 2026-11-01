"""The handoff tool must refuse unsafe targets and keep passwords owner-only."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_local_preview_accounts.py"
spec = importlib.util.spec_from_file_location("preview_account_tool", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def test_private_account_write_is_owner_only(tmp_path):
    target = tmp_path / "accounts.txt"
    target.write_text("old local handoff")
    target.chmod(0o644)
    tool.private_write(target, {"password": "synthetic-test-only"})
    assert target.stat().st_mode & 0o777 == 0o600
    assert json.loads(target.read_text()) == {"password": "synthetic-test-only"}


def test_credential_symlink_is_refused_without_touching_target(tmp_path):
    original = tmp_path / "other-account"
    original.write_text("preserve")
    link = tmp_path / "credentials"
    link.symlink_to(original)
    with pytest.raises(tool.SafeFailure, match="symlink"):
        tool.private_write(link, {"password": "synthetic-test-only"})
    assert original.read_text() == "preserve"


@pytest.mark.parametrize("url", ["https://example.test", "http://localhost:8061", "http://localhost:3061/?token=x", "http://user@localhost:3061"])
def test_nonpreview_http_target_is_refused_before_credentials(monkeypatch, url):
    checkout = SCRIPT.parents[3]
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--checkout", str(checkout), "--env", "/unused", "--url", url])
    with pytest.raises(tool.SafeFailure, match="loopback"):
        tool.main()


def test_production_environment_is_refused_before_database_connection(monkeypatch, tmp_path):
    config = tmp_path / "production.env"
    config.write_text("SOLAROPS_APP_ENV=production\nSOLAROPS_DATABASE_URL=postgresql://localhost/solarops_release_demo_61902854\n")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--checkout", str(SCRIPT.parents[3]), "--env", str(config)])
    with pytest.raises(tool.SafeFailure, match="development"):
        tool.main()
