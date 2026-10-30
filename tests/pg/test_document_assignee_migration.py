"""The assignee migration sets each existing workflow's assignee to its revision creator."""

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "b7d3e91f4a26"


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
    """Insert a project, a person and a workflow whose revision creator is that person."""
    connection = await asyncpg.connect(dsn)
    try:
        project = await connection.fetchval(
            "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
            "VALUES ('Assigned', 'ASG', 'active', now(), now()) RETURNING id"
        )
        person = await connection.fetchval(
            "INSERT INTO users (email, full_name, hashed_password, role, is_active, created_at, updated_at) "
            "VALUES ('creator@example.com', 'Creator', 'x', 'maintainer', true, now(), now()) RETURNING id"
        )
        await connection.execute(
            "INSERT INTO artefact_workflows (project_id, artefact_type, artefact_id, revision_number, revision_creator_id, phase) "
            "VALUES ($1, 'requirement', 1, 1, $2, 'Draft')",
            project,
            person,
        )
        return person
    finally:
        await connection.close()


async def _assignees(dsn):
    """Read every workflow's revision creator and assignee."""
    connection = await asyncpg.connect(dsn)
    try:
        return [
            tuple(row)
            for row in await connection.fetch(
                "SELECT revision_creator_id, assignee_id FROM artefact_workflows ORDER BY id"
            )
        ]
    finally:
        await connection.close()


def test_existing_workflows_get_their_revision_creator_as_assignee():
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    base_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    name = f"assignee_{uuid.uuid4().hex[:10]}"
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
        person = asyncio.run(_seed(dsn))
        upgraded = _alembic(url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        assert asyncio.run(_assignees(dsn)) == [(person, person)]
        downgraded = _alembic(url, "downgrade", BEFORE)
        assert downgraded.returncode == 0, downgraded.stderr
    finally:
        asyncio.run(database_command(f'DROP DATABASE "{name}" WITH (FORCE)'))
