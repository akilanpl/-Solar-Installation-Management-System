"""Environment configuration.

Values come from the process environment and, when present, the repository
root `.env`. Environment variables win over the file so tests can point at
`solarops_test` without editing developer settings.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
PLACEHOLDER_SECRETS = {
    "replace-with-a-random-32-byte-development-secret",
    "change-me",
    "changeme",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SOLAROPS_",
        env_file=str(REPO_ROOT / ".env"),
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str
    secret_key: str = Field(min_length=32)
    trusted_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    cookie_secure: bool = False
    session_ttl_hours: int = 12
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    login_ip_limit: int = 10
    login_identifier_limit: int = 8
    otp_attempt_limit: int = 8
    rate_limit_window_seconds: int = 900
    mailbox_path: str = "var/dev-mailbox.jsonl"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "solarops@localhost"
    smtp_tls: bool = True
    seed_password: str | None = None

    @field_validator("app_env")
    @classmethod
    def _env_name(cls, value: str) -> str:
        allowed = {"development", "test", "production"}
        if value not in allowed:
            raise ValueError(f"SOLAROPS_APP_ENV must be one of {sorted(allowed)}")
        return value

    @field_validator("secret_key")
    @classmethod
    def _secret(cls, value: str, info) -> str:
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and value in PLACEHOLDER_SECRETS:
            raise ValueError("Refusing the example secret key in production.")
        return value

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.trusted_origins.split(",") if item.strip()]

    @property
    def mailbox_file(self) -> Path:
        path = Path(self.mailbox_path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path

    @property
    def development_mailbox_enabled(self) -> bool:
        return self.app_env == "development" and not self.smtp_host


@lru_cache
def get_settings() -> Settings:
    return Settings()
