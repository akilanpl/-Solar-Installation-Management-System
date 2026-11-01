"""Environment configuration.

Values come from the process environment and, when present, the repository
root `.env`. Environment variables win over the file so tests can point at
`solarops_test` without editing developer settings.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
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
    trusted_proxy_ips: str = ""
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
    razorpay_key_id: str | None = None
    razorpay_key_secret: SecretStr | None = None
    razorpay_webhook_secret: SecretStr | None = None
    seed_password: str | None = None
    gst_rate_bps: int = 1800
    advance_percent: int = 40
    syscache_ttl_seconds: int = 900
    syscache_force_fallback: bool = False
    ai_model_url: str | None = None
    ai_model_key: str | None = None
    ai_model_provider_name: str | None = None
    ai_model_version: str | None = None
    weather_provider_url: str | None = None
    weather_provider_key: str | None = None
    weather_provider_name: str | None = None
    quotation_validity_days: int = 14
    evidence_dir: str = "var/survey-evidence"
    evidence_max_bytes: int = 5_000_000
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "SolarOps"
    webauthn_allowed_origins: str = ""
    webauthn_challenge_ttl_minutes: int = 5
    totp_issuer: str = "SolarOps"
    totp_window: int = 1
    mfa_recovery_code_count: int = 10
    mfa_ticket_ttl_minutes: int = 10
    mfa_max_attempts: int = 5
    mfa_lockout_minutes: int = 15
    strong_auth_ttl_minutes: int = 10
    strong_auth_roles: str = "admin,finance,support"

    @field_validator("app_env")
    @classmethod
    def _env_name(cls, value: str) -> str:
        allowed = {"development", "test", "production"}
        if value not in allowed:
            raise ValueError(f"SOLAROPS_APP_ENV must be one of {sorted(allowed)}")
        return value

    @field_validator("gst_rate_bps")
    @classmethod
    def _gst(cls, value: int) -> int:
        if value < 0 or value > 2800:
            raise ValueError("SOLAROPS_GST_RATE_BPS must be between 0 and 2800.")
        return value

    @field_validator("advance_percent")
    @classmethod
    def _advance(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("SOLAROPS_ADVANCE_PERCENT must be between 1 and 100.")
        return value

    @field_validator("secret_key")
    @classmethod
    def _secret(cls, value: str, info) -> str:
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and value in PLACEHOLDER_SECRETS:
            raise ValueError("Refusing the example secret key in production.")
        return value

    @model_validator(mode="after")
    def secure_production(self):
        if self.app_env == "production":
            if not self.cookie_secure:
                raise ValueError("Production requires Secure cookies.")
            if not self.origins or any(not origin.startswith("https://") or "*" in origin for origin in self.origins):
                raise ValueError("Production requires explicit HTTPS trusted origins.")
            if self.webauthn_rp_id in {"localhost", "127.0.0.1"}:
                raise ValueError("Production requires an explicit WebAuthn relying-party ID.")
            if any(
                not origin.startswith("https://") or "*" in origin
                for origin in self.webauthn_origins
            ):
                raise ValueError("Production requires explicit HTTPS WebAuthn origins.")
        return self

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.trusted_origins.split(",") if item.strip()]

    @property
    def webauthn_origins(self) -> list[str]:
        explicit = [
            item.strip() for item in self.webauthn_allowed_origins.split(",") if item.strip()
        ]
        return explicit or self.origins

    @property
    def strong_auth_role_set(self) -> set[str]:
        return {item.strip() for item in self.strong_auth_roles.split(",") if item.strip()}

    @property
    def mailbox_file(self) -> Path:
        path = Path(self.mailbox_path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path

    @property
    def development_mailbox_enabled(self) -> bool:
        return self.app_env == "development" and not self.smtp_host

    @property
    def evidence_path(self) -> Path:
        path = Path(self.evidence_dir)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
