"""
Application configuration.

Loads settings from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = ""
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "bloom_db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432

    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    BLOOM_APP_NAME: str = "EmbedLabs Bloom"
    BLOOM_APP_VERSION: str = "0.1.4"

    APP_BASE_URL: str = "http://localhost:8000"
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    TESTSTATION_APP_URL: str = "http://localhost:5173"

    # M1: Restrict CORS to explicit origins only (no wildcard)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "https://bloom.embedlabs.de",
    ]

    # L1: Disable API docs in production by default
    ENABLE_DOCS: bool = False

    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "changeme123"
    ADMIN_FULL_NAME: str = "Admin"

    SMTP_ENABLED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: Optional[EmailStr] = None
    SMTP_FROM_NAME: str = ""
    SMTP_REPLY_TO: Optional[EmailStr] = None
    SMTP_STARTTLS: bool = True
    SMTP_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 30

    INVITE_TOKEN_TTL_HOURS: int = 72
    EMAIL_VERIFICATION_TOKEN_TTL_HOURS: int = 24
    PASSWORD_RESET_TOKEN_TTL_HOURS: int = 2

    @model_validator(mode="after")
    def populate_database_url(self):
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
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

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
