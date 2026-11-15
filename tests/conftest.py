"""Pytest local plugins for bloom-app-backend."""

from __future__ import annotations

import os
import secrets
import socket
import string
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from tests.config import TEST_POSTGRES_PORT


def _postgres_available_from_env() -> bool:
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("BLOOM_DATABASE_URL")
    if not database_url:
        return False

    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"postgres", "postgresql"}:
        return True

    host = parsed.hostname or "localhost"
    port = parsed.port or TEST_POSTGRES_PORT

    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def api_client():
    """One TestClient per pytest session (avoids asyncpg teardown across HTTP modules)."""
    if not _postgres_available_from_env():
        pytest.skip("api_client tests require reachable Postgres for app lifespan startup")

    from app.core.deps import limiter
    from app.main import app

    limiter.enabled = False

    with TestClient(app, base_url="http://test") as client:
        yield client


def unique_suffix(length: int = 8) -> str:
    """A short token unique to this call."""
    return secrets.token_hex(length // 2)


def unique_email(stem: str = "user", domain: str = "example.com") -> str:
    return f"{stem}-{unique_suffix()}@{domain}"


def unique_prefix() -> str:
    """A three-letter project prefix, the shape Bloom validates."""
    return "".join(secrets.choice(string.ascii_uppercase) for _ in range(3))


def unique_name(stem: str = "Project") -> str:
    return f"{stem} {unique_suffix()}"


@pytest.fixture
def make_email():
    """Factory so a test can mint as many distinct addresses as it needs."""
    return unique_email


def create_project(client, headers: dict, stem: str = "Project", **overrides) -> dict:
    """Create a project, retrying past a taken prefix."""
    last = None
    for _ in range(12):
        body = {"name": unique_name(stem), "prefix": unique_prefix()}
        body.update(overrides)
        last = client.post("/api/projects", headers=headers, json=body)
        if last.status_code == 201:
            return last.json()
        if "already exists" not in last.text:
            break
    raise AssertionError(f"could not create a project: {last.status_code} {last.text}")


@pytest.fixture
def make_project():
    """Factory for a project that cannot collide with an earlier run."""
    return create_project
