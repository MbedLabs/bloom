"""The Visions migration reaches only its named holders and refuses to downgrade over visions."""

import asyncio
import json
import os
import subprocess
import sys
import uuid

import asyncpg

from tests.pg.test_access_entries_migration import ROOT, _alembic, _dsn

BEFORE = "d1f6b8a3e572"
RELEASED_MAINTAINER_SET = (
    "Requirements",
    "Specifications",
    "Standards",
    "Designs",
    "Risks",
    "Change Requests",
    "Concepts",
    "Test Cases",
    "Suites",
    "Campaigns",
    "Defects",
    "Protocols",
    "Reports",
    "Baselines",
    "Parameters",
    "Traceability",
    "Project Management",
)
COVERED = (
    "Read Internal",
    "Read Customer",
    "Review Internal",
    "Review Customer",
    "Application Administration",
)


async def _fetch(dsn: str, statement: str, *args):
    conn = await asyncpg.connect(dsn)
    try:
        return await conn.fetch(statement, *args)
    finally:
        await conn.close()


async def _value(dsn: str, statement: str, *args):
    conn = await asyncpg.connect(dsn)
    try:
        return await conn.fetchval(statement, *args)
    finally:
        await conn.close()


async def _seed(dsn: str) -> dict:
    """A released maintainer entry, a Specifications-only entry, a Specifications group and an
    editable policy."""
    conn = await asyncpg.connect(dsn)
    try:
        ids = dict(await conn.fetch("SELECT name, id FROM policies"))
        project = await conn.fetchval(
            "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
            "VALUES ('Visions', 'PRJ', 'Active', now(), now()) RETURNING id"
        )
        seeded = {"project": project}
        for key, names in (
            ("released", RELEASED_MAINTAINER_SET),
            ("spec_only", ("Specifications",)),
        ):
            user = await conn.fetchval(
                "INSERT INTO users (email, full_name, hashed_password, role, is_active, "
                "created_at, updated_at) VALUES ($1, $1, 'x', 'maintainer', true, now(), now()) "
                "RETURNING id",
                f"{key}@visions-migration.example.com",
            )
            entry = await conn.fetchval(
                "INSERT INTO project_access (project_id, user_id, owner, inherit_policies, "
                "created_at) VALUES ($1, $2, false, false, now()) RETURNING id",
                project,
                user,
            )
            for name in names:
                await conn.execute(
                    "INSERT INTO project_access_policies (access_id, policy_id) VALUES ($1, $2)",
                    entry,
                    ids[name],
                )
            seeded[key] = entry
        seeded["group"] = await conn.fetchval(
            "INSERT INTO groups (name, description, created_at, updated_at) "
            "VALUES ('Spec Writers', '', now(), now()) RETURNING id"
        )
        await conn.execute(
            "INSERT INTO group_policies (group_id, policy_id) VALUES ($1, $2)",
            seeded["group"],
            ids["Specifications"],
        )
        seeded["editable"] = await conn.fetchval(
            "INSERT INTO policies (name, description, scope, permissions, type_tags, is_default, "
            "created_at, updated_at) VALUES ('Hand made', '', 'document', $1, $2, false, now(), "
            "now()) RETURNING id",
            json.dumps({"SPEC": ["comment", "view"]}),
            json.dumps({"SPEC": {"all": True, "visibility": [], "tags": []}}),
        )
        return seeded
    finally:
        await conn.close()


async def _entry_policies(dsn: str, entry: int) -> list:
    rows = await _fetch(
        dsn,
        "SELECT p.name FROM policies p JOIN project_access_policies x ON x.policy_id = p.id "
        "WHERE x.access_id = $1 ORDER BY p.name",
        entry,
    )
    return [row["name"] for row in rows]


async def _group_policies(dsn: str, group: str) -> list:
    rows = await _fetch(
        dsn,
        "SELECT p.name FROM policies p JOIN group_policies x ON x.policy_id = p.id "
        "JOIN groups g ON g.id = x.group_id WHERE g.name = $1 ORDER BY p.name",
        group,
    )
    return [row["name"] for row in rows]


async def _state(dsn: str, seeded: dict) -> dict:
    """Every row the migration may touch, with whole rows as JSON text."""
    editable = await _fetch(
        dsn,
        "SELECT row_to_json(p)::text AS row FROM policies p WHERE id = $1",
        seeded["editable"],
    )
    group = await _fetch(
        dsn, "SELECT row_to_json(g)::text AS row FROM groups g WHERE id = $1", seeded["group"]
    )
    covered = await _fetch(
        dsn,
        "SELECT name, permissions::text AS permissions, type_tags::text AS type_tags "
        "FROM policies WHERE is_default AND name = ANY($1::text[])",
        list(COVERED),
    )
    visions = await _fetch(
        dsn,
        "SELECT scope, is_default, permissions::text AS permissions FROM policies "
        "WHERE name = 'Visions'",
    )
    return {
        "released": await _entry_policies(dsn, seeded["released"]),
        "spec_only": await _entry_policies(dsn, seeded["spec_only"]),
        "group": await _group_policies(dsn, "Spec Writers"),
        "product_owners": await _group_policies(dsn, "Product Owners"),
        "editable": [row["row"] for row in editable],
        "group_row": [row["row"] for row in group],
        "covered": {
            row["name"]: (json.loads(row["permissions"]), json.loads(row["type_tags"]))
            for row in covered
        },
        "visions": [dict(row) for row in visions],
    }


def _downgrade(url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": url, "BLOOM_DOTENV_DISABLED": "1"}
    env.pop("BLOOM_DATABASE_URL", None)
    return subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", BEFORE],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_visions_reach_only_their_holders_and_downgrade_waits_for_no_visions():
    dsn = _dsn()
    name = f"vis_{uuid.uuid4().hex[:10]}"
    base, _, _ = dsn.rpartition("/")
    asyncio.run(_value(dsn, f'CREATE DATABASE "{name}"'))
    try:
        target = f"{base}/{name}"
        url = target.replace("postgresql://", "postgresql+asyncpg://", 1)
        _alembic(url, "upgrade", BEFORE)
        seeded = asyncio.run(_seed(target))
        before = asyncio.run(_state(target, seeded))
        assert before["visions"] == []

        _alembic(url, "upgrade", "head")
        after = asyncio.run(_state(target, seeded))
        assert after["released"] == sorted((*RELEASED_MAINTAINER_SET, "Visions"))
        assert after["product_owners"] == sorted((*before["product_owners"], "Visions"))
        for key in ("spec_only", "group", "editable", "group_row"):
            assert after[key] == before[key], key
        assert [(row["scope"], row["is_default"]) for row in after["visions"]] == [
            ("document", True)
        ]
        assert set(after["covered"]) == set(COVERED)
        for policy, (permissions, type_tags) in after["covered"].items():
            assert permissions["VIS"] == permissions["SPEC"], policy
            assert type_tags["VIS"] == type_tags["SPEC"], policy
            assert {**permissions, "VIS": None} == {
                **before["covered"][policy][0],
                "VIS": None,
            }, policy

        vision = asyncio.run(
            _value(
                target,
                "INSERT INTO documents (project_id, doc_id, doc_type, title, status, version, "
                "visibility, created_at, updated_at) VALUES ($1, 'PRJ-VIS-001', 'VIS', 'Vision', "
                "'Draft', '1', 'internal', now(), now()) RETURNING id",
                seeded["project"],
            )
        )
        refused = _downgrade(url)
        assert refused.returncode != 0
        assert "Cannot downgrade below 637f976e78e0" in refused.stderr
        asyncio.run(_value(target, "DELETE FROM documents WHERE id = $1", vision))

        _alembic(url, "downgrade", BEFORE)
        assert asyncio.run(_state(target, seeded)) == before
        _alembic(url, "upgrade", "head")
        assert asyncio.run(_state(target, seeded))["released"] == after["released"]
    finally:
        asyncio.run(_value(dsn, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
