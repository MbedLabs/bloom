import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.core.config import Settings

CONFIG_ENV_KEYS = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "ADMIN_EMAIL",
    "ADMIN_FULL_NAME",
    "ADMIN_PASSWORD",
    "AUTO_SEED_ADMIN",
    "APP_BASE_URL",
    "BLOOM_ACCESS_TOKEN_EXPIRE_MINUTES",
    "BLOOM_ADMIN_EMAIL",
    "BLOOM_ADMIN_FULL_NAME",
    "BLOOM_ADMIN_PASSWORD",
    "BLOOM_AUTO_SEED_ADMIN",
    "BLOOM_APP_BASE_URL",
    "BLOOM_ATTACHMENT_DIR",
    "BLOOM_ATTACHMENT_UPLOADS_PER_15_MINUTES",
    "BLOOM_CORS_ORIGINS",
    "BLOOM_DATABASE_URL",
    "BLOOM_ENV",
    "BLOOM_EMAIL_VERIFICATION_TOKEN_TTL_HOURS",
    "BLOOM_ENABLE_DOCS",
    "BLOOM_FRONTEND_BASE_URL",
    "BLOOM_INVITE_TOKEN_TTL_HOURS",
    "BLOOM_MAX_ATTACHMENT_SIZE",
    "BLOOM_MAX_CONCURRENT_ATTACHMENT_UPLOADS_PER_USER",
    "BLOOM_MAX_DOCUMENT_ATTACHMENT_BYTES",
    "BLOOM_MIN_ATTACHMENT_FREE_BYTES",
    "BLOOM_PASSWORD_RESET_TOKEN_TTL_HOURS",
    "BLOOM_REQIF_MAX_REQUEST_BYTES",
    "BLOOM_REQIF_MAX_MEMBER_BYTES",
    "BLOOM_REQIF_MAX_ARCHIVE_ENTRIES",
    "BLOOM_REQIF_MAX_COMPRESSION_RATIO",
    "BLOOM_REQIF_MAX_OBJECTS",
    "BLOOM_REQIF_MAX_RELATIONS",
    "BLOOM_REQIF_MAX_HIERARCHY_DEPTH",
    "BLOOM_REQIF_PROCESSING_TIMEOUT_SECONDS",
    "BLOOM_REQIF_IMPORTS_PER_15_MINUTES",
    "BLOOM_REQIF_STREAM_CHUNK_BYTES",
    "BLOOM_RUN_STARTUP_DATA_REPAIR",
    "BLOOM_SECRET_KEY",
    "BLOOM_SERVICE_TOKEN_PEPPER",
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
    "APP_ENV",
    "ATTACHMENT_DIR",
    "ATTACHMENT_UPLOADS_PER_15_MINUTES",
    "EMAIL_VERIFICATION_TOKEN_TTL_HOURS",
    "ENABLE_DOCS",
    "FRONTEND_BASE_URL",
    "INVITE_TOKEN_TTL_HOURS",
    "MAX_ATTACHMENT_SIZE",
    "MAX_CONCURRENT_ATTACHMENT_UPLOADS_PER_USER",
    "MAX_DOCUMENT_ATTACHMENT_BYTES",
    "MIN_ATTACHMENT_FREE_BYTES",
    "PASSWORD_RESET_TOKEN_TTL_HOURS",
    "REQIF_MAX_REQUEST_BYTES",
    "REQIF_MAX_MEMBER_BYTES",
    "REQIF_MAX_ARCHIVE_ENTRIES",
    "REQIF_MAX_COMPRESSION_RATIO",
    "REQIF_MAX_OBJECTS",
    "REQIF_MAX_RELATIONS",
    "REQIF_MAX_HIERARCHY_DEPTH",
    "REQIF_PROCESSING_TIMEOUT_SECONDS",
    "REQIF_IMPORTS_PER_15_MINUTES",
    "REQIF_STREAM_CHUNK_BYTES",
    "RUN_STARTUP_DATA_REPAIR",
    "SECRET_KEY",
    "SERVICE_TOKEN_PEPPER",
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


def test_reqif_limits_have_public_beta_defaults(monkeypatch):
    clear_config_env(monkeypatch)
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)

    settings = Settings(_env_file=None)

    assert settings.REQIF_MAX_REQUEST_BYTES == 25 * 1024 * 1024
    assert settings.REQIF_MAX_MEMBER_BYTES == 25 * 1024 * 1024
    assert settings.REQIF_MAX_ARCHIVE_ENTRIES == 100
    assert settings.REQIF_MAX_COMPRESSION_RATIO == 20
    assert settings.REQIF_MAX_OBJECTS == 999
    assert settings.REQIF_MAX_RELATIONS == 10_000
    assert settings.REQIF_MAX_HIERARCHY_DEPTH == 100
    assert settings.REQIF_PROCESSING_TIMEOUT_SECONDS == 60
    assert settings.REQIF_IMPORTS_PER_15_MINUTES == 5
    assert settings.REQIF_STREAM_CHUNK_BYTES == 1024 * 1024


def test_attachment_upload_limits_have_public_beta_defaults(monkeypatch):
    clear_config_env(monkeypatch)
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)

    settings = Settings(_env_file=None)

    assert settings.ATTACHMENT_UPLOADS_PER_15_MINUTES == 10
    assert settings.MAX_CONCURRENT_ATTACHMENT_UPLOADS_PER_USER == 1


def test_attachment_upload_limits_read_bloom_prefixed_env(monkeypatch):
    clear_config_env(monkeypatch)
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ATTACHMENT_UPLOADS_PER_15_MINUTES", "17")
    monkeypatch.setenv("BLOOM_MAX_CONCURRENT_ATTACHMENT_UPLOADS_PER_USER", "1")

    settings = Settings(_env_file=None)

    assert settings.ATTACHMENT_UPLOADS_PER_15_MINUTES == 17
    assert settings.MAX_CONCURRENT_ATTACHMENT_UPLOADS_PER_USER == 1


def test_attachment_concurrency_cannot_exceed_database_guarantee(monkeypatch):
    clear_config_env(monkeypatch)
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_MAX_CONCURRENT_ATTACHMENT_UPLOADS_PER_USER", "2")

    import pytest

    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_reqif_member_limit_cannot_be_raised_above_25_mib(monkeypatch):
    clear_config_env(monkeypatch)
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_REQIF_MAX_MEMBER_BYTES", str(25 * 1024 * 1024 + 1))

    import pytest

    with pytest.raises(ValueError, match="25 MiB"):
        Settings(_env_file=None)


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
    monkeypatch.setenv("BLOOM_SMTP_REPLY_TO", "reply@example.com")
    monkeypatch.setenv("BLOOM_SMTP_STARTTLS", "false")
    monkeypatch.setenv("BLOOM_SMTP_SSL", "true")
    monkeypatch.setenv("BLOOM_SMTP_TIMEOUT_SECONDS", "9")
    monkeypatch.setenv("BLOOM_SMTP_FROM_NAME", "Attempted Override")

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
    assert str(settings.SMTP_REPLY_TO) == "reply@example.com"
    assert settings.SMTP_STARTTLS is False
    assert settings.SMTP_SSL is True
    assert settings.SMTP_TIMEOUT_SECONDS == 9
    assert not hasattr(settings, "SMTP_FROM_NAME")


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


def test_production_rejects_default_admin_email(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "this-is-a-long-password")

    import pytest

    with pytest.raises(ValueError, match="ADMIN_EMAIL"):
        Settings(_env_file=None)


def test_production_rejects_default_admin_password(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "changeme123")

    import pytest

    with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
        Settings(_env_file=None)


def test_production_rejects_short_admin_password(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "short-password")

    import pytest

    with pytest.raises(ValueError, match="at least 16"):
        Settings(_env_file=None)


def test_development_allows_bootstrap_defaults(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "development")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "changeme123")

    settings = Settings(_env_file=None)

    assert settings.ADMIN_EMAIL == "admin@example.com"
    assert settings.ADMIN_PASSWORD == "changeme123"


def test_development_auto_seed_admin_defaults_on(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "development")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)

    settings = Settings(_env_file=None)

    assert settings.AUTO_SEED_ADMIN is True


def test_development_startup_data_repair_defaults_on(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "development")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)

    settings = Settings(_env_file=None)

    assert settings.RUN_STARTUP_DATA_REPAIR is True


def test_production_auto_seed_admin_defaults_off(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "this-is-a-long-password")

    settings = Settings(_env_file=None)

    assert settings.AUTO_SEED_ADMIN is False


def test_production_startup_data_repair_defaults_off(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "this-is-a-long-password")

    settings = Settings(_env_file=None)

    assert settings.RUN_STARTUP_DATA_REPAIR is False


def test_production_auto_seed_admin_can_be_explicitly_enabled(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "this-is-a-long-password")
    monkeypatch.setenv("BLOOM_AUTO_SEED_ADMIN", "true")

    settings = Settings(_env_file=None)

    assert settings.AUTO_SEED_ADMIN is True


def test_production_startup_data_repair_can_be_explicitly_enabled(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "this-is-a-long-password")
    monkeypatch.setenv("BLOOM_RUN_STARTUP_DATA_REPAIR", "true")

    settings = Settings(_env_file=None)

    assert settings.RUN_STARTUP_DATA_REPAIR is True


def test_production_allows_missing_integration_encryption_key(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.delenv("BLOOM_INTEGRATION_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("INTEGRATION_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "this-is-a-long-password")

    settings = Settings(_env_file=None)

    assert settings.BLOOM_ENV == "production"
    assert settings.INTEGRATION_ENCRYPTION_KEY == ""


def test_production_allows_invalid_key_until_tracker_integration_is_used(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "this-is-a-long-password")
    monkeypatch.setenv("BLOOM_INTEGRATION_ENCRYPTION_KEY", "not-a-valid-fernet-key")

    settings = Settings(_env_file=None)

    assert settings.INTEGRATION_ENCRYPTION_KEY == "not-a-valid-fernet-key"


def test_production_accepts_valid_integration_encryption_key(monkeypatch):
    from cryptography.fernet import Fernet

    clear_config_env(monkeypatch)

    monkeypatch.setenv("BLOOM_ENV", "production")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)
    monkeypatch.setenv("BLOOM_ADMIN_EMAIL", "ops@embedlabs.net")
    monkeypatch.setenv("BLOOM_ADMIN_PASSWORD", "this-is-a-long-password")
    monkeypatch.setenv("BLOOM_INTEGRATION_ENCRYPTION_KEY", Fernet.generate_key().decode())

    settings = Settings(_env_file=None)

    assert settings.BLOOM_ENV == "production"


def test_development_allows_missing_integration_encryption_key(monkeypatch):
    clear_config_env(monkeypatch)

    monkeypatch.delenv("BLOOM_INTEGRATION_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("INTEGRATION_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("BLOOM_ENV", "development")
    monkeypatch.setenv("BLOOM_SECRET_KEY", "b" * 32)

    settings = Settings(_env_file=None)

    assert settings.INTEGRATION_ENCRYPTION_KEY == ""
