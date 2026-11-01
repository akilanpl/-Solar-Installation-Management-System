import pytest
from app.api.deps import client_ip
from app.core.config import Settings
from fastapi import Request
from pydantic import ValidationError


@pytest.mark.parametrize("changes", [{"cookie_secure": False}, {"trusted_origins": "http://insecure.example"}, {"trusted_origins": "https://*.example.com"}])
def test_production_rejects_insecure_config(changes):
    base = dict(app_env="production", database_url="postgresql+psycopg:///unused", secret_key="runtime-test-secret-long-enough-123456", cookie_secure=True, trusted_origins="https://solar.example")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{**base, **changes})


def test_forwarded_ip_requires_explicit_trusted_proxy():
    from types import SimpleNamespace
    settings = SimpleNamespace(trusted_proxy_ips="")
    request = Request({"type": "http", "headers": [(b"x-forwarded-for", b"198.51.100.1")], "client": ("127.0.0.1", 1234), "app": SimpleNamespace(state=SimpleNamespace(settings=settings))})
    assert client_ip(request) == "127.0.0.1"
    settings.trusted_proxy_ips = "127.0.0.1"
    assert client_ip(request) == "198.51.100.1"
