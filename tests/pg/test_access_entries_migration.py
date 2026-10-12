"""The access-entries migration seeds the default policies and groups and converts the
1.1.0 project memberships of a database at the revision before it (real PostgreSQL)."""

import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest

from app.core.permissions import DOC_TYPE_RESOURCES, RESOURCE_ACTIONS
from app.core.policy_seed import DEFAULT_GROUPS, DEFAULT_POLICIES

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "e1a7c3f9b204"


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _alembic(url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": url, "BLOOM_DOTENV_DISABLED": "1"}
    env.pop("BLOOM_DATABASE_URL", None)
    done = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr


async def _seed(dsn: str) -> dict:
    conn = await asyncpg.connect(dsn)
    try:
        ids = {}
        for key, role in [
            ("maintainer", "maintainer"),
            ("viewer", "maintainer"),
            ("chosen", "external"),
            ("every", "external"),
            ("empty", "external"),
            ("admin", "admin"),
        ]:
            ids[key] = await conn.fetchval(
                "INSERT INTO users (email, full_name, hashed_password, role, is_active, "
                "created_at, updated_at) VALUES ($1, $2, 'x', $3, true, now(), now()) "
                "RETURNING id",
                f"{key}@example.com",
                key,
                role,
            )
        ids["project"] = await conn.fetchval(
            "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
            "VALUES ('Alpha', 'ALP', 'active', now(), now()) RETURNING id"
        )
        for user, role, types in [
            ("maintainer", "maintainer", []),
            ("viewer", "external", []),
            ("chosen", "external", ["REQ", "TC"]),
            ("every", "external", list(DOC_TYPE_RESOURCES)),
            ("empty", "external", []),
            ("admin", "maintainer", []),
        ]:
            membership = await conn.fetchval(
                "INSERT INTO project_memberships (user_id, project_id, role, created_at, "
                "updated_at) VALUES ($1, $2, $3, now(), now()) RETURNING id",
                ids[user],
                ids["project"],
                role,
            )
            for doc_type in types:
                await conn.execute(
                    "INSERT INTO project_external_doc_types (membership_id, doc_type) "
                    "VALUES ($1, $2)",
                    membership,
                    doc_type,
                )
        return ids
    finally:
        await conn.close()


async def _state(dsn: str) -> dict:
    conn = await asyncpg.connect(dsn)
    try:
        policies = {
            row["name"]: row
            for row in await conn.fetch(
                "SELECT name, description, scope, is_default, permissions::text AS permissions, "
                "type_tags::text AS type_tags FROM policies"
            )
        }
        entries = {
            row["user_id"]: (row["owner"], row["names"])
            for row in await conn.fetch(
                "SELECT a.user_id, a.owner, array_agg(p.name ORDER BY p.name) AS names "
                "FROM project_access a JOIN project_access_policies ap ON ap.access_id = a.id "
                "JOIN policies p ON p.id = ap.policy_id GROUP BY a.id"
            )
        }
        groups = {
            row["name"]: row["names"]
            for row in await conn.fetch(
                "SELECT g.name, array_agg(p.name ORDER BY p.name) AS names "
                "FROM groups g JOIN group_policies gp ON gp.group_id = g.id "
                "JOIN policies p ON p.id = gp.policy_id GROUP BY g.id"
            )
        }
        members = await conn.fetchval("SELECT count(*) FROM group_memberships")
        roles = {row["id"]: row["role"] for row in await conn.fetch("SELECT id, role FROM users")}
        creator = await conn.fetchval(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'requirements' AND column_name = 'created_by_id'"
        )
        return {
            "policies": policies,
            "entries": entries,
            "groups": groups,
            "creator": creator,
            "members": members,
            "roles": roles,
        }
    finally:
        await conn.close()


async def _tables(dsn: str) -> set:
    conn = await asyncpg.connect(dsn)
    try:
        return {
            row["table_name"]
            for row in await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
        }
    finally:
        await conn.close()


def test_the_access_migration_seeds_defaults_and_converts_memberships():
    dsn = _dsn()
    name = f"k75_{uuid.uuid4().hex[:10]}"
    base, _, _ = dsn.rpartition("/")

    async def admin(statement: str) -> None:
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(statement)
        finally:
            await conn.close()

    asyncio.run(admin(f'CREATE DATABASE "{name}"'))
    try:
        target = f"{base}/{name}"
        url = target.replace("postgresql://", "postgresql+asyncpg://", 1)
        _alembic(url, "upgrade", BEFORE)
        ids = asyncio.run(_seed(target))
        _alembic(url, "upgrade", "head")
        state = asyncio.run(_state(target))
        policies, entries = state["policies"], state["entries"]

        _alembic(url, "downgrade", "-1")
        assert not {"policies", "groups", "project_access", "tags"} & asyncio.run(_tables(target))
        _alembic(url, "upgrade", "head")
        assert asyncio.run(_state(target)) == state

        assert {n for n, row in policies.items() if row["is_default"]} == {
            spec["name"] for spec in DEFAULT_POLICIES
        }
        assert len([row for row in policies.values() if row["is_default"]]) == 23
        for spec in DEFAULT_POLICIES:
            stored = policies[spec["name"]]
            assert stored["scope"] == spec["scope"]
            assert stored["description"] == spec["description"]
            assert json.loads(stored["permissions"]) == spec["permissions"]
            assert json.loads(stored["type_tags"]) == spec["type_tags"]
        assert state["groups"] == {
            spec["name"]: sorted(spec["policy_names"]) for spec in DEFAULT_GROUPS
        }
        assert state["members"] == 0
        assert state["creator"] == 1
        assert entries[ids["maintainer"]] == (
            False,
            sorted(
                spec["name"]
                for spec in DEFAULT_POLICIES
                if spec["name"]
                not in {
                    "Read Internal",
                    "Read Customer",
                    "Review Internal",
                    "Review Customer",
                    "Access Management",
                    "Application Administration",
                }
            ),
        )
        assert entries[ids["viewer"]] == (False, ["Released Read-only"])
        assert entries[ids["every"]] == (False, ["Released Read (all document types)"])
        assert entries[ids["chosen"]] == (False, ["Released Read (REQ, TC)"])
        assert entries[ids["empty"]] == (False, ["Released Read (no document types)"])
        assert ids["admin"] not in entries
        for user in ("maintainer", "viewer"):
            assert state["roles"][ids[user]] == "maintainer"
        for user in ("every", "chosen", "empty"):
            assert state["roles"][ids[user]] == "external"
        assert state["roles"][ids["admin"]] == "admin"
        assert set(entries) == {
            ids[user] for user in ("maintainer", "viewer", "every", "chosen", "empty")
        }
        for name in (
            "Released Read-only",
            "Released Read (all document types)",
            "Released Read (REQ, TC)",
            "Released Read (no document types)",
        ):
            row = policies[name]
            assert row["is_default"] is False
            permissions = json.loads(row["permissions"])
            assert "parameter" not in permissions
            assert all(set(actions) <= {"view", "comment"} for actions in permissions.values())
            assert not any(scope.get("all") for scope in json.loads(row["type_tags"]).values())
        chosen = policies["Released Read (REQ, TC)"]
        assert json.loads(chosen["type_tags"]) == {
            "REQ": {"visibility": ["customer"], "tags": []},
            "TC": {"visibility": ["customer"], "tags": []},
        }
        assert "SPEC" not in json.loads(chosen["permissions"])
        assert set(json.loads(policies["Released Read (no document types)"]["permissions"])) == {
            "baseline",
            "link",
            "project",
        }
        assert set(json.loads(policies["Released Read (all document types)"]["type_tags"])) == set(
            DOC_TYPE_RESOURCES
        )
        assert all(
            rule == {"visibility": ["customer"], "tags": []}
            for rule in json.loads(
                policies["Released Read (all document types)"]["type_tags"]
            ).values()
        )
        assert all(
            rule == {"visibility": ["internal", "customer"], "tags": []}
            for rule in json.loads(policies["Released Read-only"]["type_tags"]).values()
        )
        full = {}
        for name in entries[ids["maintainer"]][1]:
            for resource, actions in json.loads(policies[name]["permissions"]).items():
                full.setdefault(resource, set()).update(actions)
        assert full == {
            resource: actions - ({"review"} if resource in {"CMP", "RPT", "RSK", "STD"} else set())
            for resource, actions in RESOURCE_ACTIONS.items()
            if resource not in {"users", "access", "application"}
        }

        environment = {
            **os.environ,
            "DATABASE_URL": url,
            "BLOOM_DOTENV_DISABLED": "1",
            "ADMIN_EMAIL": "access-validation@example.com",
            "ADMIN_PASSWORD": "ci-admin-password-123",
            "AUTO_SEED_ADMIN": "true",
            "RUN_STARTUP_DATA_REPAIR": "false",
        }
        for key in (
            "BLOOM_DATABASE_URL",
            "BLOOM_ADMIN_EMAIL",
            "BLOOM_ADMIN_PASSWORD",
            "BLOOM_AUTO_SEED_ADMIN",
            "BLOOM_RUN_STARTUP_DATA_REPAIR",
        ):
            environment.pop(key, None)
        checked = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/api/test_group_owned_policies_http.py",
                "tests/api/test_group_bulk_members_http.py",
                "tests/api/test_groups_http.py",
                "tests/api/test_group_permissions_http.py",
                "tests/api/test_project_policy_grants_http.py",
                "tests/api/test_project_access_entries_http.py",
                "tests/logic/test_entitlements.py",
                "tests/logic/test_app_policy_scope.py",
                "tests/logic/test_policy_action_separation.py",
                "tests/api/test_document_attachments_http.py::TestHoldingFilesAgainstADocument::test_write_cannot_remove_a_file_without_delete",
                "-q",
                "--tb=short",
                "--disable-warnings",
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        assert checked.returncode == 0, checked.stdout + checked.stderr
        print(checked.stdout)

    finally:
        asyncio.run(admin(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
