"""The CLI session migration keeps existing rows and concurrent CLI steps succeed once
(real PostgreSQL)."""

import asyncio
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import User
from app.models.cli_auth_session import CliAuthSession
from app.services import cli_auth
from app.services.token_service import hash_token, invalidate_all_refresh_tokens
from tests.api.test_cli_auth import CHALLENGE, PREFIX, VERIFIER

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "d6f9b2c3a0e5"
HEAD = "8134a1512496"


def _dsn() -> str:
    """Return the test database connection as a plain PostgreSQL DSN."""
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _alembic(url: str, *args: str) -> str:
    """Run the Alembic command line against the given database."""
    env = {**os.environ, "DATABASE_URL": url, "BLOOM_DOTENV_DISABLED": "1"}
    env.pop("BLOOM_DATABASE_URL", None)
    done = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


async def _admin(dsn: str, statement: str) -> None:
    """Run one maintenance statement on the test server."""
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(statement)
    finally:
        await conn.close()


@contextmanager
def _own_database():
    """Create a uniquely named database and drop it afterwards."""
    dsn = _dsn()
    name = f"cli_auth_{uuid.uuid4().hex[:10]}"
    base, _, _ = dsn.rpartition("/")
    asyncio.run(_admin(dsn, f'CREATE DATABASE "{name}"'))
    try:
        yield f"{base}/{name}"
    finally:
        asyncio.run(_admin(dsn, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


async def _seed_before(target: str) -> dict:
    """Insert an account, a project, a refresh token and an audit event at the old head."""
    conn = await asyncpg.connect(target)
    try:
        user = await conn.fetchval(
            "INSERT INTO users (email, full_name, hashed_password, role, is_active, "
            "session_version, created_at, updated_at) VALUES ('retained@example.com', "
            "'Retained', 'unused', 'maintainer', true, 3, now(), now()) RETURNING id"
        )
        project = await conn.fetchval(
            "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
            "VALUES ('Retained project', 'RET', 'active', now(), now()) RETURNING id"
        )
        await conn.execute(
            "INSERT INTO user_tokens (user_id, purpose, token_hash, expires_at, created_at) "
            "VALUES ($1, 'refresh', 'retained-hash', now() + interval '1 day', now())",
            user,
        )
        await conn.execute(
            "INSERT INTO audit_events (occurred_at, actor_type, actor_user_id, action, outcome) "
            "VALUES (now(), 'user', $1, 'auth.login', 'success')",
            user,
        )
        return {"user": user, "project": project}
    finally:
        await conn.close()


async def _state(target: str, ids: dict) -> dict:
    """Read the retained rows, the revision and the CLI session table's shape."""
    conn = await asyncpg.connect(target)
    try:
        has_table = await conn.fetchval(
            "SELECT to_regclass('public.cli_auth_sessions') IS NOT NULL"
        )
        state = {
            "revision": await conn.fetchval("SELECT version_num FROM alembic_version"),
            "version": await conn.fetchval(
                "SELECT session_version FROM users WHERE id=$1", ids["user"]
            ),
            "project": await conn.fetchval("SELECT name FROM projects WHERE id=$1", ids["project"]),
            "token": await conn.fetchval(
                "SELECT token_hash FROM user_tokens WHERE user_id=$1", ids["user"]
            ),
            "audit": await conn.fetchval(
                "SELECT count(*) FROM audit_events WHERE actor_user_id=$1", ids["user"]
            ),
            "table": has_table,
        }
        if has_table:
            state["columns"] = {
                row["column_name"]: (row["data_type"], row["is_nullable"])
                for row in await conn.fetch(
                    "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                    "WHERE table_name='cli_auth_sessions'"
                )
            }
            state["indexes"] = {
                row["indexname"]
                for row in await conn.fetch(
                    "SELECT indexname FROM pg_indexes WHERE tablename='cli_auth_sessions'"
                )
            }
            state["cascade"] = await conn.fetchval(
                "SELECT delete_rule FROM information_schema.referential_constraints "
                "WHERE constraint_name='cli_auth_sessions_user_id_fkey'"
            )
            state["check"] = await conn.fetchval(
                "SELECT count(*) FROM pg_constraint WHERE conname='ck_cli_auth_mode'"
            )
            state["sessions"] = await conn.fetchval("SELECT count(*) FROM cli_auth_sessions")
        return state
    finally:
        await conn.close()


async def _add_sessions(target: str, user: int) -> None:
    """Insert one pending and one approved CLI session."""
    conn = await asyncpg.connect(target)
    try:
        await conn.execute(
            "INSERT INTO cli_auth_sessions (id, client_name, mode, code_challenge, state, "
            "expires_at, created_at) VALUES ($1, 'Pending client', 'code', $2, 'state', "
            "now() + interval '10 minutes', now())",
            uuid.uuid4(),
            CHALLENGE,
        )
        await conn.execute(
            "INSERT INTO cli_auth_sessions (id, client_name, mode, redirect_uri, code_challenge, "
            "state, exchange_code_hash, user_id, approved_session_version, expires_at, "
            "created_at) VALUES ($1, 'Approved client', 'callback', "
            "'http://127.0.0.1:8123/callback', $2, 'state', $3, $4, 3, "
            "now() + interval '10 minutes', now())",
            uuid.uuid4(),
            CHALLENGE,
            hash_token("approved-code"),
            user,
        )
    finally:
        await conn.close()


def test_cli_migration_upgrades_downgrades_with_sessions_and_reupgrades():
    with _own_database() as target:
        url = target.replace("postgresql://", "postgresql+asyncpg://", 1)
        _alembic(url, "upgrade", BEFORE)
        ids = asyncio.run(_seed_before(target))
        before = asyncio.run(_state(target, ids))
        assert before["revision"] == BEFORE and before["table"] is False

        _alembic(url, "upgrade", "head")
        upgraded = asyncio.run(_state(target, ids))
        retained = {k: before[k] for k in ("version", "project", "token", "audit")}
        assert {k: upgraded[k] for k in retained} == retained
        assert upgraded["revision"] == HEAD
        expected = {column.name: column.nullable for column in CliAuthSession.__table__.columns}
        assert {name: info[1] == "YES" for name, info in upgraded["columns"].items()} == expected
        assert upgraded["indexes"] == {"cli_auth_sessions_pkey", "ix_cli_auth_sessions_expires_at"}
        assert upgraded["cascade"] == "CASCADE"
        assert upgraded["check"] == 1
        assert upgraded["sessions"] == 0

        asyncio.run(_add_sessions(target, ids["user"]))
        assert asyncio.run(_state(target, ids))["sessions"] == 2
        _alembic(url, "downgrade", "-1")
        downgraded = asyncio.run(_state(target, ids))
        assert downgraded["revision"] == BEFORE and downgraded["table"] is False
        assert {k: downgraded[k] for k in retained} == retained

        _alembic(url, "upgrade", "head")
        reupgraded = asyncio.run(_state(target, ids))
        assert reupgraded == {**upgraded, "sessions": 0}
        assert f"{HEAD} (head)" in _alembic(url, "heads")


def test_cli_migration_on_a_fresh_database_reaches_the_single_head():
    with _own_database() as target:
        url = target.replace("postgresql://", "postgresql+asyncpg://", 1)
        _alembic(url, "upgrade", "head")
        assert _alembic(url, "heads").split() == [HEAD, "(head)"]

        async def revision():
            conn = await asyncpg.connect(target)
            try:
                return await conn.fetchval("SELECT version_num FROM alembic_version")
            finally:
                await conn.close()

        assert asyncio.run(revision()) == HEAD


def _race(request):
    """Send four copies of one request at the same time."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        return [future.result() for future in [pool.submit(request) for _ in range(4)]]


def test_cli_approval_exchange_and_refresh_succeed_once_on_postgresql(api_client):
    api_client.cookies.clear()
    login = api_client.post(
        "/api/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD}
    )
    assert login.status_code == 200, login.text
    api_client.cookies.clear()
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    session = api_client.post(
        PREFIX + "/start",
        json={
            "client_name": "Concurrent client",
            "mode": "code",
            "code_challenge": CHALLENGE,
            "state": "race-state",
        },
    )
    assert session.status_code == 200, session.text
    session_id = session.json()["session_id"]
    approved = _race(
        lambda: api_client.post(
            PREFIX + "/approve", headers=headers, json={"session_id": session_id}
        )
    )
    assert [r.status_code for r in approved].count(200) == 1
    assert all(r.status_code in (200, 400) for r in approved)
    code = next(r.json()["exchange_code"] for r in approved if r.status_code == 200)
    exchanged = _race(
        lambda: api_client.post(
            PREFIX + "/exchange",
            json={"session_id": session_id, "code": code, "code_verifier": VERIFIER},
        )
    )
    assert [r.status_code for r in exchanged].count(200) == 1
    assert all(r.status_code in (200, 400) for r in exchanged)
    tokens = next(r.json() for r in exchanged if r.status_code == 200)
    refreshed = _race(
        lambda: api_client.post(
            PREFIX + "/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
    )
    assert [r.status_code for r in refreshed].count(200) == 1
    assert all(r.status_code in (200, 401) for r in refreshed)


def test_cli_refresh_waits_for_and_honours_an_account_revocation():
    with _own_database() as target:
        url = target.replace("postgresql://", "postgresql+asyncpg://", 1)
        _alembic(url, "upgrade", "head")

        async def check():
            engine = create_async_engine(url)
            maker = async_sessionmaker(engine, expire_on_commit=False)
            attempted_user_lock = asyncio.Event()

            def before_execute(conn, cursor, statement, parameters, context, executemany):
                if "FROM users" in statement and "FOR " in statement:
                    attempted_user_lock.set()

            async with maker() as seed:
                user = User(
                    email="revocation@example.com",
                    full_name="Revocation",
                    hashed_password="unused",
                    is_active=True,
                )
                seed.add(user)
                await seed.flush()
                user_id = user.id
                await seed.execute(
                    text(
                        "INSERT INTO user_tokens (user_id, purpose, token_hash, expires_at, "
                        "created_at) VALUES (:user_id, 'refresh', :digest, "
                        "now() + interval '1 day', now())"
                    ),
                    {"user_id": user_id, "digest": hash_token("race-refresh")},
                )
                await seed.commit()

            async def refresh():
                async with maker() as request:
                    try:
                        value = await cli_auth.refresh_credentials(request, "race-refresh")
                        await request.commit()
                        return value
                    except cli_auth.CliAuthorizationError as exc:
                        await request.rollback()
                        return exc.reason

            try:
                async with maker() as revoker:
                    account = await revoker.scalar(
                        select(User).where(User.id == user_id).with_for_update()
                    )
                    event.listen(engine.sync_engine, "before_cursor_execute", before_execute)
                    task = asyncio.create_task(refresh())
                    await asyncio.wait_for(attempted_user_lock.wait(), 5)
                    await revoker.execute(text("SET LOCAL lock_timeout='1s'"))
                    account.session_version += 1
                    await invalidate_all_refresh_tokens(revoker, user_id)
                    await revoker.commit()
                    assert await asyncio.wait_for(task, 5) == "invalid_token"
            finally:
                await engine.dispose()

        asyncio.run(check())
