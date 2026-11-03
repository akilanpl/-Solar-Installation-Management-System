"""CI must never migrate a developer/production/shared or implicit database."""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("prepare_browser_ci", SCRIPTS / "prepare_browser_ci.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def environment():
    return {"SOLAROPS_APP_ENV": "development", "SOLAROPS_BROWSER_DATABASE_NAME": "solarops_browser_ci", "SOLAROPS_SEED_PASSWORD": "ephemeral-fixture-12345"}


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://ci@remote.example/solarops_browser_ci",
    "postgresql+psycopg://ci@127.0.0.1/solarops",
    "postgresql+psycopg://ci@127.0.0.1/solarops_release_demo_20261102",
    "postgresql+psycopg://ci@127.0.0.1/solarops_test",
])
def test_unsafe_database_rejected(url):
    with pytest.raises(ValueError):
        runner.validate_target(url, environment())


@pytest.mark.parametrize("key,value", [
    ("SOLAROPS_APP_ENV", "production"),
    ("SOLAROPS_BROWSER_DATABASE_NAME", ""),
    ("SOLAROPS_SEED_PASSWORD", "short"),
    ("SOLAROPS_RAZORPAY_KEY_ID", "provider-key"),
    ("SOLAROPS_RAZORPAY_KEY_SECRET", "provider-secret"),
    ("SOLAROPS_RAZORPAY_WEBHOOK_SECRET", "provider-secret"),
    ("SOLAROPS_SMTP_HOST", "external-email.example"),
])
def test_unsafe_environment_rejected(key, value):
    env = {**environment(), key: value}
    with pytest.raises(ValueError):
        runner.validate_target("postgresql+psycopg://ci@127.0.0.1/solarops_browser_ci", env)


def test_explicit_disposable_database_accepted():
    runner.validate_target("postgresql+psycopg://ci@127.0.0.1/solarops_browser_ci", environment())


def test_nonempty_database_refused_before_migration(monkeypatch):
    env = {**environment(), "SOLAROPS_DATABASE_URL": "postgresql+psycopg://ci@127.0.0.1/solarops_browser_ci", "SOLAROPS_SECRET_KEY": "e" * 32}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(runner, "build_engine", lambda _: object())
    class Nonempty:
        def get_table_names(self):
            return ["users"]
    monkeypatch.setattr(runner, "inspect", lambda _: Nonempty())
    monkeypatch.setattr(runner.subprocess, "run", lambda *_a, **_k: pytest.fail("Migrated a nonempty database"))
    with pytest.raises(ValueError, match="not empty"):
        runner.main()
