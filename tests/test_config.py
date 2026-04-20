import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.core.config import Settings

CONFIG_ENV_KEYS = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "ADMIN_EMAIL",
    "ADMIN_FULL_NAME",
    "ADMIN_PASSWORD",
    "APP_BASE_URL",
    "BLOOM_ACCESS_TOKEN_EXPIRE_MINUTES",
    "BLOOM_ADMIN_EMAIL",
    "BLOOM_ADMIN_FULL_NAME",
    "BLOOM_ADMIN_PASSWORD",
    "BLOOM_APP_BASE_URL",
    "BLOOM_CORS_ORIGINS",
    "BLOOM_DATABASE_URL",
    "BLOOM_EMAIL_VERIFICATION_TOKEN_TTL_HOURS",
    "BLOOM_ENABLE_DOCS",
    "BLOOM_FRONTEND_BASE_URL",
    "BLOOM_INVITE_TOKEN_TTL_HOURS",
    "BLOOM_PASSWORD_RESET_TOKEN_TTL_HOURS",
    "BLOOM_SECRET_KEY",
    "BLOOM_SMTP_ENABLED",
    "BLOOM_SMTP_FROM_EMAIL",
    "BLOOM_SMTP_FROM_NAME",
    "BLOOM_SMTP_HOST",
    "BLOOM_SMTP_PASSWORD",
    "BLOOM_SMTP_PORT",
    "BLOOM_SMTP_REPLY_TO",
    "BLOOM_SMTP_SSL",
    "BLOOM_SMTP_STARTTLS",
    "BLOOM_SMTP_TIMEOUT_SECONDS",
    "BLOOM_SMTP_USERNAME",
    "BLOOM_TESTSTATION_APP_URL",
    "CORS_ORIGINS",
    "DATABASE_URL",
    "EMAIL_VERIFICATION_TOKEN_TTL_HOURS",
    "ENABLE_DOCS",
    "FRONTEND_BASE_URL",
    "INVITE_TOKEN_TTL_HOURS",
    "PASSWORD_RESET_TOKEN_TTL_HOURS",
    "SECRET_KEY",
    "SMTP_ENABLED",
    "SMTP_FROM_EMAIL",
    "SMTP_FROM_NAME",
    "SMTP_HOST",
    "SMTP_PASSWORD",
    "SMTP_PORT",
    "SMTP_REPLY_TO",
    "SMTP_SSL",
    "SMTP_STARTTLS",
    "SMTP_TIMEOUT_SECONDS",
    "SMTP_USERNAME",
    "TESTSTATION_APP_URL",
]


def clear_config_env(monkeypatch):
    for key in CONFIG_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_settings_reads_bloom_prefixed_env(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv(
        "BLOOM_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/bloom_db"
    )
    monkeypatch.setenv("BLOOM_ACCESS_TOKEN_EXPIRE_MINUTES", "42")
    monkeypatch.setenv("BLOOM_APP_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("BLOOM_FRONTEND_BASE_URL", "http://localhost:5173")
    monkeypatch.setenv("BLOOM_TESTSTATION_APP_URL", "http://localhost:5174")
    monkeypatch.setenv("BLOOM_CORS_ORIGINS", '["http://localhost:5173"]')
    monkeypatch.setenv("BLOOM_ENABLE_DOCS", "true")
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("BLOOM_ADMIN_FULL_NAME", "Bloom Admin")
    monkeypatch.setenv("BLOOM_INVITE_TOKEN_TTL_HOURS", "48")
    monkeypatch.setenv("BLOOM_EMAIL_VERIFICATION_TOKEN_TTL_HOURS", "6")
    monkeypatch.setenv("BLOOM_PASSWORD_RESET_TOKEN_TTL_HOURS", "3")
    monkeypatch.setenv("BLOOM_SMTP_ENABLED", "true")
    monkeypatch.setenv("BLOOM_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("BLOOM_SMTP_PORT", "2525")
    monkeypatch.setenv("BLOOM_SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("BLOOM_SMTP_PASSWORD", "smtp-password")
    monkeypatch.setenv("BLOOM_SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("BLOOM_SMTP_FROM_NAME", "Bloom Mailer")
    monkeypatch.setenv("BLOOM_SMTP_REPLY_TO", "reply@example.com")
    monkeypatch.setenv("BLOOM_SMTP_STARTTLS", "false")
    monkeypatch.setenv("BLOOM_SMTP_SSL", "true")
    monkeypatch.setenv("BLOOM_SMTP_TIMEOUT_SECONDS", "9")

    settings = Settings(_env_file=None)

    assert settings.SECRET_KEY == "b" * 32
    assert settings.DATABASE_URL == "postgresql+asyncpg://postgres:postgres@localhost:5432/bloom_db"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 42
    assert settings.APP_BASE_URL == "http://localhost:8000"
    assert settings.FRONTEND_BASE_URL == "http://localhost:5173"
    assert settings.TESTSTATION_APP_URL == "http://localhost:5174"
    assert settings.CORS_ORIGINS == ["http://localhost:5173"]
    assert settings.ENABLE_DOCS is True
    assert settings.ADMIN_EMAIL == "admin@example.com"
    assert settings.ADMIN_PASSWORD == "admin-password"
    assert settings.ADMIN_FULL_NAME == "Bloom Admin"
    assert settings.INVITE_TOKEN_TTL_HOURS == 48
    assert settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS == 6
    assert settings.PASSWORD_RESET_TOKEN_TTL_HOURS == 3
    assert settings.SMTP_ENABLED is True
    assert settings.SMTP_HOST == "smtp.example.com"
    assert settings.SMTP_PORT == 2525
    assert settings.SMTP_USERNAME == "smtp-user"
    assert settings.SMTP_PASSWORD == "smtp-password"
    assert str(settings.SMTP_FROM_EMAIL) == "noreply@example.com"
    assert settings.SMTP_FROM_NAME == "Bloom Mailer"
    assert str(settings.SMTP_REPLY_TO) == "reply@example.com"
    assert settings.SMTP_STARTTLS is False
    assert settings.SMTP_SSL is True
    assert settings.SMTP_TIMEOUT_SECONDS == 9


def test_settings_falls_back_to_unprefixed_env(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("SMTP_ENABLED", "true")
    monkeypatch.setenv("SMTP_HOST", "smtp.unprefixed.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")

    settings = Settings(_env_file=None)

    assert settings.SECRET_KEY == "s" * 32
    assert settings.SMTP_ENABLED is True
    assert settings.SMTP_HOST == "smtp.unprefixed.example.com"
    assert str(settings.SMTP_FROM_EMAIL) == "noreply@example.com"


def test_settings_prefers_bloom_prefixed_env(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("SMTP_HOST", "smtp.unprefixed.example.com")
    monkeypatch.setenv("BLOOM_SMTP_HOST", "smtp.bloom-prefixed.example.com")

    settings = Settings(_env_file=None)

    assert settings.SECRET_KEY == "b" * 32
    assert settings.SMTP_HOST == "smtp.bloom-prefixed.example.com"
