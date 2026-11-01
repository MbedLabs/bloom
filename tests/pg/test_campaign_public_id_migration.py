"""The public ID migration gives every campaign a public ID, makes suite and campaign public IDs
unique and refuses duplicates (real PostgreSQL)."""

import asyncio
import os
import subprocess
import sys

import asyncpg
import pytest

from tests.pg.test_cli_auth_migration import ROOT, _alembic, _own_database

BEFORE = "0ef8b87db4d3"
REVISION = "b2d4f6a8c0e1"


def _alembic_result(url: str, *args: str) -> subprocess.CompletedProcess:
    """Run the Alembic command line against the database and return its result."""
    env = {**os.environ, "DATABASE_URL": url, "BLOOM_DOTENV_DISABLED": "1"}
    env.pop("BLOOM_DATABASE_URL", None)
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


async def _project(conn, name: str, prefix: str) -> int:
    """Insert a project and return its id."""
    return await conn.fetchval(
        "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
        "VALUES ($1, $2, 'active', now(), now()) RETURNING id",
        name,
        prefix,
    )


async def _campaign(conn, project: int, public_id: str | None) -> int:
    """Insert a campaign with the public ID, or none, and return its id."""
    return await conn.fetchval(
        "INSERT INTO test_campaigns (project_id, campaign_id, name, status, visibility, "
        "created_at, updated_at) VALUES ($1, $2, 'Demo', 'Planned', 'internal', now(), now()) "
        "RETURNING id",
        project,
        public_id,
    )


async def _suite(conn, project: int, public_id: str) -> int:
    """Insert a suite with the public ID and return its id."""
    return await conn.fetchval(
        "INSERT INTO test_suites (project_id, suite_id, name, status, visibility, "
        "created_at, updated_at) VALUES ($1, $2, 'Demo', 'Draft', 'internal', now(), now()) "
        "RETURNING id",
        project,
        public_id,
    )


async def _seed_campaigns(target: str) -> dict[str, list[int]]:
    """Insert campaigns with and without public IDs in three projects."""
    conn = await asyncpg.connect(target)
    try:
        prj = await _project(conn, "Demo", "PRJ")
        abc = await _project(conn, "Demo ABC", "ABC")
        xyz = await _project(conn, "Demo XYZ", "XYZ")
        return {
            "PRJ": [
                await _campaign(conn, prj, None),
                await _campaign(conn, prj, "PRJ-CMP-002"),
                await _campaign(conn, prj, ""),
                await _campaign(conn, prj, None),
            ],
            "ABC": [await _campaign(conn, abc, None)],
            "XYZ": [
                await _campaign(conn, xyz, "XYZ-CMP-005"),
                await _campaign(conn, xyz, "XYZ-CMP-999"),
                await _campaign(conn, xyz, None),
            ],
        }
    finally:
        await conn.close()


async def _public_ids(target: str) -> dict[int, str | None]:
    """Every campaign's public ID by its id."""
    conn = await asyncpg.connect(target)
    try:
        rows = await conn.fetch("SELECT id, campaign_id FROM test_campaigns")
        return {row["id"]: row["campaign_id"] for row in rows}
    finally:
        await conn.close()


async def _shape(target: str) -> dict:
    """Whether the campaign public ID is nullable, the unique indexes, and the revision."""
    conn = await asyncpg.connect(target)
    try:
        nullable = await conn.fetchval(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'test_campaigns' AND column_name = 'campaign_id'"
        )
        indexes = await conn.fetch(
            "SELECT indexname FROM pg_indexes WHERE indexname IN "
            "('uq_test_suites_suite_id', 'uq_test_campaigns_campaign_id')"
        )
        revision = await conn.fetchval("SELECT version_num FROM alembic_version")
        return {
            "nullable": nullable,
            "indexes": sorted(row["indexname"] for row in indexes),
            "revision": revision,
        }
    finally:
        await conn.close()


def test_every_campaign_gets_a_public_id_and_both_public_ids_become_unique():
    with _own_database() as target:
        url = target.replace("postgresql://", "postgresql+asyncpg://", 1)
        _alembic(url, "upgrade", BEFORE)
        ids = asyncio.run(_seed_campaigns(target))

        _alembic(url, "upgrade", REVISION)
        public = asyncio.run(_public_ids(target))
        assert [public[i] for i in ids["PRJ"]] == [
            "PRJ-CMP-003",
            "PRJ-CMP-002",
            "PRJ-CMP-004",
            "PRJ-CMP-005",
        ]
        assert [public[i] for i in ids["ABC"]] == ["ABC-CMP-001"]
        assert [public[i] for i in ids["XYZ"]] == ["XYZ-CMP-0005", "XYZ-CMP-0999", "XYZ-CMP-1000"]
        assert asyncio.run(_shape(target)) == {
            "nullable": "NO",
            "indexes": ["uq_test_campaigns_campaign_id", "uq_test_suites_suite_id"],
            "revision": REVISION,
        }

        async def duplicates():
            conn = await asyncpg.connect(target)
            try:
                project = await conn.fetchval("SELECT id FROM projects WHERE prefix = 'PRJ'")
                await _suite(conn, project, "PRJ-TS-001")
                with pytest.raises(asyncpg.UniqueViolationError):
                    await _suite(conn, project, "PRJ-TS-001")
                with pytest.raises(asyncpg.UniqueViolationError):
                    await _campaign(conn, project, "PRJ-CMP-002")
                with pytest.raises(asyncpg.NotNullViolationError):
                    await _campaign(conn, project, None)
            finally:
                await conn.close()

        asyncio.run(duplicates())

        _alembic(url, "downgrade", BEFORE)
        assert asyncio.run(_shape(target)) == {"nullable": "YES", "indexes": [], "revision": BEFORE}
        assert asyncio.run(_public_ids(target)) == public

        _alembic(url, "upgrade", "head")
        assert asyncio.run(_shape(target))["indexes"] == [
            "uq_test_campaigns_campaign_id",
            "uq_test_suites_suite_id",
        ]


@pytest.mark.parametrize(
    "seed, column",
    [
        (("PRJ-TS-001", "PRJ-TS-001", None, None), "test_suites.suite_id"),
        ((None, None, "PRJ-CMP-001", "PRJ-CMP-001"), "test_campaigns.campaign_id"),
    ],
)
def test_the_migration_refuses_duplicate_public_ids(seed, column):
    first_suite, second_suite, first_campaign, second_campaign = seed
    with _own_database() as target:
        url = target.replace("postgresql://", "postgresql+asyncpg://", 1)
        _alembic(url, "upgrade", BEFORE)

        async def insert():
            conn = await asyncpg.connect(target)
            try:
                prj = await _project(conn, "Demo", "PRJ")
                abc = await _project(conn, "Demo ABC", "ABC")
                for project, suite in ((prj, first_suite), (abc, second_suite)):
                    if suite:
                        await _suite(conn, project, suite)
                for project, campaign in ((prj, first_campaign), (abc, second_campaign)):
                    if campaign:
                        await _campaign(conn, project, campaign)
            finally:
                await conn.close()

        asyncio.run(insert())
        refused = _alembic_result(url, "upgrade", "head")
        assert refused.returncode != 0
        assert f"{column} holds duplicate public IDs" in refused.stderr
        assert asyncio.run(_shape(target))["revision"] == BEFORE
