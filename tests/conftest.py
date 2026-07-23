"""Pytest local plugins for bloom-app-backend."""

from __future__ import annotations

import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

# Workspace `.env` lives at `budProject/.env` (parent of `bloom-app-backend/`).


def _load_workspace_dotenv_into_environ() -> None:
    """Parse monorepo `.env` into ``os.environ`` for keys not already set (no ``python-dotenv`` dep)."""
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


if os.environ.get("BLOOM_DOTENV_DISABLED") == "1":
    # CI / explicit pytest: shell env wins; strip bloom-prefixed DB so ``DATABASE_URL`` alone applies.
    os.environ.pop("BLOOM_DATABASE_URL", None)
else:
    _load_workspace_dotenv_into_environ()
    if "SECRET_KEY" not in os.environ and os.environ.get("BLOOM_SECRET_KEY"):
        os.environ["SECRET_KEY"] = os.environ["BLOOM_SECRET_KEY"]

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")
os.environ.setdefault("BLOOM_DISABLE_RATE_LIMIT", "1")


def _postgres_available_from_env() -> bool:
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("BLOOM_DATABASE_URL")
    if not database_url:
        return False

    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return True

    host = parsed.hostname or "localhost"
    port = parsed.port or 5432

    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def api_client():
    """One TestClient per pytest session — avoids asyncpg teardown across HTTP modules."""
    if not _postgres_available_from_env():
        pytest.skip("api_client tests require reachable Postgres for app lifespan startup")

    from app.core.deps import limiter
    from app.main import app

    # This suite drives many real logins across a single client IP within a
    # minute; the login rate limiter (10/min) is not what these flows test, so
    # disable it here to avoid cross-test 429s. The DB-backed import-attempt
    # limiter (its own 429 tests) is independent and unaffected.
    limiter.enabled = False

    with TestClient(app, base_url="http://test") as client:
        yield client
