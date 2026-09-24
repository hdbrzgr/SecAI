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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
