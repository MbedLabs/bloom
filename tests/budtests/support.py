"""Isolation and helpers for the in-process suites: test-only settings set before the app is
imported, temporary environment variables and attributes, and in-memory SQLite sessions."""

import asyncio
import contextlib
import os
import re
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DEV_POSTGRES_PORTS = frozenset({5432, 5433, 5434})
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
TEST_DATABASE_NAME = re.compile(r"/(test_bloom|bloom_[a-z0-9_]+)")
MISSING = object()


def _check_database_url(url: str) -> None:
    """Refuse any database but in-memory SQLite or a loopback PostgreSQL on a test port."""
    parsed = urlparse(url)
    if parsed.scheme.startswith("sqlite"):
        if url not in {"sqlite:///:memory:", "sqlite+aiosqlite:///:memory:"}:
            raise RuntimeError("In-process suites require an in-memory SQLite database")
        return
    if (
        parsed.scheme not in {"postgresql", "postgresql+asyncpg"}
        or parsed.hostname not in LOOPBACK_HOSTS
        or parsed.port is None
        or parsed.port in DEV_POSTGRES_PORTS
        or not 1024 < parsed.port < 65536
        or not TEST_DATABASE_NAME.fullmatch(parsed.path)
    ):
        raise RuntimeError("In-process suites require a loopback test PostgreSQL, not a dev one")


def isolate() -> None:
    """Set test-only settings for every Bloom setting the app reads at import time."""
    from cryptography.fernet import Fernet

    database_url = os.environ.get("BUDTEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    _check_database_url(database_url)
    values = {
        "DOTENV_DISABLED": "1",
        "SECRET_KEY": "test-secret-key-for-ci-at-least-32-characters-long",
        "SERVICE_TOKEN_PEPPER": "test-service-token-pepper-for-ci-at-least-32-characters-long",
        "INTEGRATION_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "ADMIN_EMAIL": "admin@example.com",
        "ADMIN_PASSWORD": "ci-admin-password-123",
        "ADMIN_FULL_NAME": "CI Admin",
        "DATABASE_URL": database_url,
        "SMTP_ENABLED": "false",
        "SMTP_HOST": "127.0.0.1",
        "SMTP_FROM_EMAIL": "noreply@example.com",
        "STORAGE_BACKEND": "local",
        "APP_BASE_URL": "http://localhost:8000",
        "FRONTEND_BASE_URL": "http://localhost:8000",
        "AUTO_SEED_ADMIN": "true",
        "RUN_STARTUP_DATA_REPAIR": "false",
        "INTEGRATION_SYNC_MINUTES": "0",
        "ENV": "development",
    }
    for key, value in values.items():
        for prefix in ("", "BLOOM_"):
            os.environ[prefix + key] = value
    for key in ("SMTP_REPLY_TO", "DB_USER", "DB_PASSWORD", "DB_NAME", "DB_HOST", "DB_PORT"):
        for prefix in ("", "BLOOM_"):
            os.environ.pop(prefix + key, None)
    for key in tuple(os.environ):
        if key.startswith("AWS_"):
            os.environ.pop(key, None)
    os.environ.update(
        {
            "AWS_ACCESS_KEY_ID": "test-access-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret-key",
            "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
            "AWS_CONFIG_FILE": "/dev/null",
            "AWS_EC2_METADATA_DISABLED": "true",
            "AWS_DEFAULT_REGION": "us-east-1",
            "APP_ENV": "development",
            "BLOOM_DISABLE_RATE_LIMIT": "1",
        }
    )


@contextlib.contextmanager
def env(**values: Any) -> Iterator[None]:
    """Set environment variables for the block (None removes one) and restore them after."""
    saved = {key: os.environ.get(key, MISSING) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        yield
    finally:
        for key, value in saved.items():
            if value is MISSING:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextlib.contextmanager
def cleared_env(keys) -> Iterator[None]:
    """Remove the given environment variables for the block and restore them after."""
    with env(**{key: None for key in keys}):
        yield


@contextlib.contextmanager
def patched(target: Any, name: str, value: Any) -> Iterator[None]:
    """Replace an attribute for the block and restore it after."""
    saved = getattr(target, name, MISSING)
    setattr(target, name, value)
    try:
        yield
    finally:
        if saved is MISSING:
            delattr(target, name)
        else:
            setattr(target, name, saved)


def run(coro):
    """Run a coroutine to completion and return its result."""
    return asyncio.run(coro)


@contextlib.asynccontextmanager
async def sqlite_session():
    """An AsyncSession on a fresh in-memory SQLite database holding every Bloom table."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    import app.models  # noqa: F401
    from app.core.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


isolate()
