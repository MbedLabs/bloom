"""
Application configuration.

Loads settings from environment variables with sensible defaults.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import AliasChoices, EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILES = (BACKEND_DIR / ".env",)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        case_sensitive=True,
        extra="ignore",
        populate_by_name=True,
    )

    DATABASE_URL: str = Field(
        default="", validation_alias=AliasChoices("BLOOM_DATABASE_URL", "DATABASE_URL")
    )
    DB_USER: str = Field(
        default="postgres", validation_alias=AliasChoices("BLOOM_DB_USER", "DB_USER")
    )
    DB_PASSWORD: str = Field(
        default="postgres", validation_alias=AliasChoices("BLOOM_DB_PASSWORD", "DB_PASSWORD")
    )
    DB_NAME: str = Field(
        default="bloom_db", validation_alias=AliasChoices("BLOOM_DB_NAME", "DB_NAME")
    )
    DB_HOST: str = Field(
        default="localhost", validation_alias=AliasChoices("BLOOM_DB_HOST", "DB_HOST")
    )
    DB_PORT: int = Field(default=5432, validation_alias=AliasChoices("BLOOM_DB_PORT", "DB_PORT"))

    BLOOM_ENV: str = Field(
        default="development", validation_alias=AliasChoices("BLOOM_ENV", "APP_ENV")
    )

    SECRET_KEY: str = Field(
        default="", validation_alias=AliasChoices("BLOOM_SECRET_KEY", "SECRET_KEY")
    )
    # Short-lived access token: kept small because a rotating refresh-token
    # cookie (below) silently renews it. A leaked access token is now valid for
    # minutes, not a week.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "BLOOM_ACCESS_TOKEN_EXPIRE_MINUTES", "ACCESS_TOKEN_EXPIRE_MINUTES"
        ),
    )
    # Refresh token lifetime (delivered as an httpOnly cookie, rotated on every
    # use, revocable via the user_tokens table).
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "BLOOM_REFRESH_TOKEN_EXPIRE_DAYS", "REFRESH_TOKEN_EXPIRE_DAYS"
        ),
    )
    # Set the Secure flag on the refresh cookie. None -> on in production, off
    # elsewhere so local HTTP dev still receives the cookie.
    AUTH_COOKIE_SECURE: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("BLOOM_AUTH_COOKIE_SECURE", "AUTH_COOKIE_SECURE"),
    )

    BLOOM_APP_NAME: str = "EmbedLabs Bloom"
    BLOOM_APP_VERSION: str = "1.0.0"

    APP_BASE_URL: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices("BLOOM_APP_BASE_URL", "APP_BASE_URL"),
    )
    FRONTEND_BASE_URL: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices("BLOOM_FRONTEND_BASE_URL", "FRONTEND_BASE_URL"),
    )

    TESTSTATION_APP_URL: str = Field(
        default="http://localhost:8001",
        validation_alias=AliasChoices("BLOOM_TESTSTATION_APP_URL", "TESTSTATION_APP_URL"),
    )

    # M1: Restrict CORS to explicit origins only (no wildcard)
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:8000",
            "http://localhost:8001",
        ],
        validation_alias=AliasChoices("BLOOM_CORS_ORIGINS", "CORS_ORIGINS"),
    )

    # L1: Disable API docs in production by default
    ENABLE_DOCS: bool = Field(
        default=False, validation_alias=AliasChoices("BLOOM_ENABLE_DOCS", "ENABLE_DOCS")
    )

    # Observability
    LOG_LEVEL: str = Field(
        default="INFO", validation_alias=AliasChoices("BLOOM_LOG_LEVEL", "LOG_LEVEL")
    )
    # None -> JSON logs in production, human-readable text elsewhere
    LOG_JSON: bool | None = Field(
        default=None, validation_alias=AliasChoices("BLOOM_LOG_JSON", "LOG_JSON")
    )
    ENABLE_METRICS: bool = Field(
        default=True, validation_alias=AliasChoices("BLOOM_ENABLE_METRICS", "ENABLE_METRICS")
    )

    # Run legacy startup data repair (prefer Alembic in production)
    RUN_STARTUP_DATA_REPAIR: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("BLOOM_RUN_STARTUP_DATA_REPAIR", "RUN_STARTUP_DATA_REPAIR"),
    )

    # Explicit startup admin bootstrap; defaults on in development, off in production.
    AUTO_SEED_ADMIN: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("BLOOM_AUTO_SEED_ADMIN", "AUTO_SEED_ADMIN"),
    )

    ADMIN_EMAIL: str = Field(
        default="admin@example.com",
        validation_alias=AliasChoices("BLOOM_ADMIN_EMAIL", "ADMIN_EMAIL"),
    )
    ADMIN_PASSWORD: str = Field(
        default="changeme123",
        validation_alias=AliasChoices("BLOOM_ADMIN_PASSWORD", "ADMIN_PASSWORD"),
    )
    ADMIN_FULL_NAME: str = Field(
        default="Admin", validation_alias=AliasChoices("BLOOM_ADMIN_FULL_NAME", "ADMIN_FULL_NAME")
    )

    SMTP_ENABLED: bool = Field(
        default=False, validation_alias=AliasChoices("BLOOM_SMTP_ENABLED", "SMTP_ENABLED")
    )
    SMTP_HOST: str = Field(
        default="", validation_alias=AliasChoices("BLOOM_SMTP_HOST", "SMTP_HOST")
    )
    SMTP_PORT: int = Field(
        default=587, validation_alias=AliasChoices("BLOOM_SMTP_PORT", "SMTP_PORT")
    )
    SMTP_USERNAME: str = Field(
        default="", validation_alias=AliasChoices("BLOOM_SMTP_USERNAME", "SMTP_USERNAME")
    )
    SMTP_PASSWORD: str = Field(
        default="", validation_alias=AliasChoices("BLOOM_SMTP_PASSWORD", "SMTP_PASSWORD")
    )
    SMTP_FROM_EMAIL: Optional[EmailStr] = Field(
        default=None, validation_alias=AliasChoices("BLOOM_SMTP_FROM_EMAIL", "SMTP_FROM_EMAIL")
    )
    SMTP_REPLY_TO: Optional[EmailStr] = Field(
        default=None, validation_alias=AliasChoices("BLOOM_SMTP_REPLY_TO", "SMTP_REPLY_TO")
    )
    SMTP_STARTTLS: bool = Field(
        default=True, validation_alias=AliasChoices("BLOOM_SMTP_STARTTLS", "SMTP_STARTTLS")
    )
    SMTP_SSL: bool = Field(
        default=False, validation_alias=AliasChoices("BLOOM_SMTP_SSL", "SMTP_SSL")
    )
    SMTP_TIMEOUT_SECONDS: int = Field(
        default=30,
        validation_alias=AliasChoices("BLOOM_SMTP_TIMEOUT_SECONDS", "SMTP_TIMEOUT_SECONDS"),
    )

    INVITE_TOKEN_TTL_HOURS: int = Field(
        default=72,
        validation_alias=AliasChoices("BLOOM_INVITE_TOKEN_TTL_HOURS", "INVITE_TOKEN_TTL_HOURS"),
    )
    EMAIL_VERIFICATION_TOKEN_TTL_HOURS: int = Field(
        default=24,
        validation_alias=AliasChoices(
            "BLOOM_EMAIL_VERIFICATION_TOKEN_TTL_HOURS", "EMAIL_VERIFICATION_TOKEN_TTL_HOURS"
        ),
    )
    PASSWORD_RESET_TOKEN_TTL_HOURS: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "BLOOM_PASSWORD_RESET_TOKEN_TTL_HOURS", "PASSWORD_RESET_TOKEN_TTL_HOURS"
        ),
    )

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        """Let CI/pytest bypass workspace `.env` when injecting `DATABASE_URL` / secrets via the shell."""
        if os.environ.get("BLOOM_DOTENV_DISABLED") == "1":
            return init_settings, env_settings, file_secret_settings
        return init_settings, env_settings, dotenv_settings, file_secret_settings

    @model_validator(mode="after")
    def populate_database_url(self):
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return self

    @model_validator(mode="after")
    def default_auto_seed_admin(self):
        if self.RUN_STARTUP_DATA_REPAIR is None:
            self.RUN_STARTUP_DATA_REPAIR = self.BLOOM_ENV.lower() != "production"
        if self.AUTO_SEED_ADMIN is None:
            self.AUTO_SEED_ADMIN = self.BLOOM_ENV.lower() != "production"
        if self.LOG_JSON is None:
            self.LOG_JSON = self.BLOOM_ENV.lower() == "production"
        if self.AUTH_COOKIE_SECURE is None:
            self.AUTH_COOKIE_SECURE = self.BLOOM_ENV.lower() == "production"
        return self

    @model_validator(mode="after")
    def reject_unsafe_admin_defaults_in_production(self):
        if self.BLOOM_ENV.lower() != "production":
            return self
        if self.ADMIN_EMAIL == "admin@example.com":
            raise ValueError("ADMIN_EMAIL must be changed before production startup.")
        if self.ADMIN_PASSWORD == "changeme123":
            raise ValueError("ADMIN_PASSWORD must be changed before production startup.")
        if len(self.ADMIN_PASSWORD) < 16:
            raise ValueError("ADMIN_PASSWORD must be at least 16 characters long in production.")
        return self

    # C1: SECRET_KEY must be set explicitly — no insecure fallback in production
    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        insecure_placeholders = {
            "",
            "your-secret-key-change-in-production",
            "change-me-in-production",
            "secret",
        }
        if v in insecure_placeholders:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
