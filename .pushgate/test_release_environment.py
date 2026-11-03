"""A fixture generator must reject shared data and external integrations."""
import importlib.util
import unittest
from pathlib import Path


class ReleaseFixtureSafetyTests(unittest.TestCase):
    def test_target_and_provider_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("release_seed", root / "apps/api/scripts/prepare_release_campaign.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        safe = {"SOLAROPS_DATABASE_URL": "postgresql+psycopg://ci@127.0.0.1/solarops_browser_release_ci",
                "SOLAROPS_APP_ENV": "development", "SOLAROPS_RELEASE_DATABASE_OWNED": "true"}
        self.assertEqual(module.assert_safe(safe).database, "solarops_browser_release_ci")
        for key, value in [
            ("SOLAROPS_DATABASE_URL", "postgresql+psycopg://ci@remote.example/solarops_browser_release_ci"),
            ("SOLAROPS_DATABASE_URL", "postgresql+psycopg://ci@127.0.0.1/solarops_dev"),
            ("SOLAROPS_DATABASE_URL", "postgresql+psycopg://ci@127.0.0.1/solarops_test"),
            ("SOLAROPS_APP_ENV", "production"), ("SOLAROPS_RELEASE_DATABASE_OWNED", "false"),
            ("SOLAROPS_RAZORPAY_KEY_ID", "provider-disabled-fixture"),
            ("SOLAROPS_RAZORPAY_KEY_SECRET", "provider-disabled-fixture"),
            ("SOLAROPS_RAZORPAY_WEBHOOK_SECRET", "provider-disabled-fixture"),
            ("SOLAROPS_SMTP_HOST", "external.example"),
        ]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                module.assert_safe({**safe, key: value})
