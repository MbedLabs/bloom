"""The requirement parent migration drops requirements.parent_id and keeps every requirement."""

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "c4e8a2f6b1d3"


def _alembic(url, *arguments):
    """Run a migration against the test-owned database without operator configuration."""
    environment = {**os.environ, "DATABASE_URL": url, "BLOOM_DOTENV_DISABLED": "1"}
    environment.pop("BLOOM_DATABASE_URL", None)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )


async def _seed(dsn):
    """Insert a project and two requirements, the second pointing at the first."""
    connection = await asyncpg.connect(dsn)
    try:
        project = await connection.fetchval(
            "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
            "VALUES ('Flat', 'FLT', 'active', now(), now()) RETURNING id"
        )
        first = await connection.fetchval(
            "INSERT INTO requirements (project_id, req_id, title, status, priority, req_type, "
            "req_origin, visibility, created_at, updated_at) VALUES ($1, 'FLT-REQ-001', 'One', "
            "'Draft', 'Medium', 'Functional', 'Internal', 'internal', now(), now()) RETURNING id",
            project,
        )
        await connection.execute(
            "INSERT INTO requirements (project_id, parent_id, req_id, title, status, priority, "
            "req_type, req_origin, visibility, created_at, updated_at) VALUES ($1, $2, "
            "'FLT-REQ-002', 'Two', 'Draft', 'Medium', 'Functional', 'Internal', 'internal', "
            "now(), now())",
            project,
            first,
        )
    finally:
        await connection.close()


async def _state(dsn):
    """Read the requirement ids and whether requirements has a parent_id column."""
    connection = await asyncpg.connect(dsn)
    try:
        req_ids = [
            row["req_id"]
            for row in await connection.fetch("SELECT req_id FROM requirements ORDER BY req_id")
        ]
        has_parent = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'requirements' AND column_name = 'parent_id')"
        )
        return req_ids, has_parent
    finally:
        await connection.close()


def test_upgrade_drops_the_parent_column_and_keeps_the_requirements():
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    base_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    name = f"reqflat_{uuid.uuid4().hex[:10]}"
    dsn = f"{base_dsn.rsplit('/', 1)[0]}/{name}"
    url = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)

    async def database_command(statement):
        connection = await asyncpg.connect(base_dsn)
        try:
            await connection.execute(statement)
        finally:
            await connection.close()

    asyncio.run(database_command(f'CREATE DATABASE "{name}"'))
    try:
        before = _alembic(url, "upgrade", BEFORE)
        assert before.returncode == 0, before.stderr
        asyncio.run(_seed(dsn))
        upgraded = _alembic(url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        assert asyncio.run(_state(dsn)) == (["FLT-REQ-001", "FLT-REQ-002"], False)
        downgraded = _alembic(url, "downgrade", BEFORE)
        assert downgraded.returncode == 0, downgraded.stderr
        assert asyncio.run(_state(dsn)) == (["FLT-REQ-001", "FLT-REQ-002"], True)
    finally:
        asyncio.run(database_command(f'DROP DATABASE "{name}" WITH (FORCE)'))
