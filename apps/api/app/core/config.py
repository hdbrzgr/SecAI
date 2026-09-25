from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_KEY = "change-me-in-production-this-is-not-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SECAI_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"

    # Used to derive the key that encrypts MFA secrets at rest. Generate with:
    #   python -c "import secrets; print(secrets.token_urlsafe(48))"
    secret_key: str = INSECURE_DEFAULT_KEY

    database_url: str = "postgresql+asyncpg://secai:secai@localhost:5432/secai"
    redis_url: str = "redis://localhost:6379/0"

    # Public origin of the web app; state-changing requests must come from it.
    web_origin: str = "http://localhost:3000"

    allow_registration: bool = True
    password_min_length: int = Field(default=12, ge=8)

    session_idle_minutes: int = 60 * 12
    session_max_age_hours: int = 24 * 14
    # Login must be completed with a TOTP code within this window when MFA is on.
    mfa_pending_minutes: int = 5

    login_rate_limit_per_ip: int = 20
    login_rate_limit_per_email: int = 10
    login_rate_limit_window_seconds: int = 15 * 60

    # Scanning
    # Development/testing only: lets targets resolve to private or loopback addresses.
    # Refused in production, where it would turn the scanner into an SSRF tool.
    scan_allow_private: bool = False
    scans_per_day_per_org: int = 20
    max_targets_per_org: int = 25
    # Ownership must have been proven within this many days before each scan.
    verification_max_age_days: int = 90
    nuclei_path: str = "nuclei"
    nuclei_templates: str | None = None
    scan_tool_timeout_seconds: int = 15 * 60
    # OWASP ZAP daemon (the "zap" service in docker-compose). Unset = ZAP is skipped.
    zap_url: str | None = None
    zap_api_key: str | None = None
    zap_spider_minutes: int = 5

    # Outgoing email (verification, password reset, scan finished). Unset host = no email.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "SecAI <secai@localhost>"
    # "starttls" (port 587), "tls" (implicit TLS, port 465) or "none" (local relay only).
    smtp_security: Literal["starttls", "tls", "none"] = "starttls"
    # When SMTP is configured, new accounts must verify their email before adding websites.
    require_email_verification: bool = True

    # AI analysis with Claude. Enabled when an Anthropic API key is available
    # (SECAI_ANTHROPIC_API_KEY, or the SDK's usual ANTHROPIC_API_KEY).
    anthropic_api_key: str | None = None
    ai_model: str = "claude-opus-5"
    ai_effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"
    # Server-side refusal fallbacks (Claude API only; turn off behind proxies that reject it).
    ai_fallbacks: bool = True
    ai_max_findings: int = 60

    @property
    def ai_api_key(self) -> str | None:
        import os

        return self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY") or None

    @property
    def cookie_secure(self) -> bool:
        return self.web_origin.startswith("https://")

    @property
    def session_cookie_name(self) -> str:
        # The __Host- prefix makes browsers require Secure, Path=/ and no Domain.
        return "__Host-secai_session" if self.cookie_secure else "secai_session"

    @model_validator(mode="after")
    def _check_production(self) -> "Settings":
        if self.env == "production":
            if self.secret_key == INSECURE_DEFAULT_KEY or len(self.secret_key) < 32:
                raise ValueError("SECAI_SECRET_KEY must be set to a random value of 32+ chars")
            if not self.cookie_secure:
                raise ValueError("SECAI_WEB_ORIGIN must use https:// in production")
            if self.scan_allow_private:
                raise ValueError("SECAI_SCAN_ALLOW_PRIVATE must not be enabled in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
