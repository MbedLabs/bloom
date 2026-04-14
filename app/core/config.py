"""
Application configuration.

Loads settings from environment variables with sensible defaults.
"""

import secrets
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bloom_db"

    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    BLOOM_APP_NAME: str = "EmbedLabs Bloom"
    BLOOM_APP_VERSION: str = "0.1.0"

    TESTSTATION_APP_URL: str = "http://localhost:5173"

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    ENABLE_DOCS: bool = True

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
            v = secrets.token_hex(32)
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
