"""Overlapping project groups migrate without losing existing access entries."""

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "8134a1512496"


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


async def _snapshot(dsn):
    """Read exact access rows, policies, account roles, indexes and revision."""
    connection = await asyncpg.connect(dsn)
    try:
        return {
            "entries": [
                dict(row)
                for row in await connection.fetch("SELECT * FROM project_access ORDER BY id")
            ],
            "policies": [
                tuple(row)
                for row in await connection.fetch(
                    "SELECT * FROM project_access_policies ORDER BY access_id, policy_id"
                )
            ],
            "roles": [
                tuple(row)
                for row in await connection.fetch("SELECT id, role FROM users ORDER BY id")
            ],
            "indexes": [
                tuple(row)
                for row in await connection.fetch(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'project_access' ORDER BY indexname"
                )
            ],
            "revision": await connection.fetchval("SELECT version_num FROM alembic_version"),
        }
    finally:
        await connection.close()


async def _seed(dsn):
    """Create legacy Owner, inherited, direct policy, bundle and group-principal entries."""
    connection = await asyncpg.connect(dsn)
    try:
        project = await connection.fetchval(
            "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
            "VALUES ('Overlap', 'OVL', 'active', now(), now()) RETURNING id"
        )
        people = []
        for index in range(4):
            people.append(
                await connection.fetchval(
                    "INSERT INTO users (email, full_name, hashed_password, role, is_active, created_at, updated_at) "
                    "VALUES ($1, 'Person', 'x', 'maintainer', true, now(), now()) RETURNING id",
                    f"person-{index}@example.com",
                )
            )
        groups = dict(await connection.fetch("SELECT name, id FROM groups"))
        policy = await connection.fetchval("SELECT id FROM policies WHERE name = 'Read Customer'")
        for index, person in enumerate(people):
            entry = await connection.fetchval(
                "INSERT INTO project_access (project_id, user_id, owner, inherit_policies, policy_group_id, created_at) "
                "VALUES ($1, $2, $3, $4, $5, now()) RETURNING id",
                project,
                person,
                index == 0,
                index == 1,
                groups["Developers"] if index == 3 else None,
            )
            if index == 2:
                await connection.execute(
                    "INSERT INTO project_access_policies VALUES ($1, $2)", entry, policy
                )
        await connection.execute(
            "INSERT INTO project_access (project_id, group_id, owner, inherit_policies, created_at) "
            "VALUES ($1, $2, false, true, now())",
            project,
            groups["Testers"],
        )
        return project, people, groups
    finally:
        await connection.close()


async def _add_overlap(dsn, project, people, groups):
    """Insert a second bundle and check exact duplicates and legacy uniqueness."""
    connection = await asyncpg.connect(dsn)
    try:
        statement = (
            "INSERT INTO project_access (project_id, user_id, policy_group_id, owner, inherit_policies, created_at) "
            "VALUES ($1, $2, $3, false, false, now()) RETURNING id"
        )
        entry = await connection.fetchval(statement, project, people[3], groups["Testers"])
        with pytest.raises(asyncpg.UniqueViolationError):
            await connection.fetchval(statement, project, people[3], groups["Testers"])
        with pytest.raises(asyncpg.UniqueViolationError):
            await connection.fetchval(statement, project, people[0], None)
        return entry
    finally:
        await connection.close()


def test_overlap_migration_preserves_rows_and_refuses_lossy_downgrade():
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    base_dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    name = f"overlap_{uuid.uuid4().hex[:10]}"
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
        initial = _alembic(url, "upgrade", BEFORE)
        assert initial.returncode == 0, initial.stderr
        project, people, groups = asyncio.run(_seed(dsn))
        before = asyncio.run(_snapshot(dsn))
        upgraded = _alembic(url, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr
        after = asyncio.run(_snapshot(dsn))
        for field in ("entries", "policies", "roles"):
            assert after[field] == before[field]
        extra = asyncio.run(_add_overlap(dsn, project, people, groups))
        overlapping = asyncio.run(_snapshot(dsn))
        refused = _alembic(url, "downgrade", BEFORE)
        assert refused.returncode != 0
        assert "overlapping project groups" in refused.stderr.lower()
        assert asyncio.run(_snapshot(dsn)) == overlapping

        async def remove_test_entry():
            connection = await asyncpg.connect(dsn)
            try:
                await connection.execute("DELETE FROM project_access WHERE id = $1", extra)
            finally:
                await connection.close()

        asyncio.run(remove_test_entry())
        downgraded = _alembic(url, "downgrade", BEFORE)
        assert downgraded.returncode == 0, downgraded.stderr
        assert asyncio.run(_snapshot(dsn)) == before
        upgraded_again = _alembic(url, "upgrade", "head")
        assert upgraded_again.returncode == 0, upgraded_again.stderr
        assert asyncio.run(_snapshot(dsn)) == after
    finally:
        asyncio.run(database_command(f'DROP DATABASE "{name}" WITH (FORCE)'))
