"""
* @file     ${tests/bloom_pg_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface of Bloom's PostgreSQL tests: a new database per test, migrations and races.
* @author   Amine El Omari
* @date     2026-11-09
* @version  1.0.0
* @note     Each test creates its own database on the CI PostgreSQL and drops it afterwards.
"""

import asyncio
import contextlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI
from sqlalchemy import bindparam, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import cli_auth as cli_auth_api
from app.api import integrations
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import limiter
from app.core.security import create_access_token
from app.models.cli_auth_session import CliAuthSession
from app.models.user import User, UserRole
from app.services import cli_auth, integration_sync
from app.services.token_service import hash_token, invalidate_all_refresh_tokens
from tests.bloom_interface import BloomInterface

REAL_CLIENT = httpx.AsyncClient
ROOT = Path(__file__).resolve().parents[1]


class BloomPgInterface(BloomInterface):

    def _release_database(self):
        if getattr(self, "pg_database", None):
            self._run(self._drop_postgres_database())
            self.pg_database = None

    def bloom_use_postgres(self, tables=True):
        url = os.environ.get(self.parameters.DATABASE_SETTING, "")
        if not url.startswith(self.parameters.POSTGRES_SCHEME):
            return False
        parts = urlsplit(url)
        self._run(self.engine.dispose())
        if getattr(self, "pg_database", None):
            self._run(self._drop_postgres_database())
        self.pg_admin_url = urlunsplit(parts._replace(path=f"/{self.parameters.PG_ADMIN_DATABASE}"))
        self.pg_database = f"{self.parameters.PG_DATABASE_PREFIX}{uuid.uuid4().hex[:12]}"
        self._run(self._create_postgres_database())
        self.pg_url = urlunsplit(parts._replace(path=f"/{self.pg_database}"))
        self.engine = create_async_engine(self.pg_url)
        if tables:
            self._run(self._create_tables())
        self.maker = async_sessionmaker(self.engine, expire_on_commit=False)
        return True

    def bloom_run_alembic(self, *args):
        self._run(self.engine.dispose())
        env = {**os.environ, self.parameters.DATABASE_SETTING: self.pg_url}
        env["BLOOM_DOTENV_DISABLED"] = "1"
        env.pop("BLOOM_DATABASE_URL", None)
        done = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        return done.returncode, done.stdout + done.stderr

    def bloom_list_alembic_heads(self):
        _, output = self.bloom_run_alembic("heads")
        return [line.split()[0] for line in output.splitlines() if "(head)" in line]

    def bloom_read_revision(self):
        return self._run(self._fetch_value("SELECT version_num FROM alembic_version"))

    def bloom_seed_retained_rows(self):
        return self._run(self._seed_retained_rows())

    def bloom_read_retained_rows(self, ids):
        return self._run(self._read_retained_rows(ids))

    def bloom_read_cli_session_table(self):
        return self._run(self._read_cli_session_table())

    def bloom_cli_session_model_columns(self):
        return {column.name: column.nullable for column in CliAuthSession.__table__.columns}

    def bloom_add_cli_sessions(self, user_id):
        self._run(self._add_cli_sessions(user_id))

    def bloom_start_cli_api(self):
        app = FastAPI()
        app.state.limiter = limiter
        app.include_router(cli_auth_api.router, prefix=self.parameters.CLI_PREFIX)
        app.dependency_overrides[get_db] = self._serve_session
        self.patches.enter_context(patch.object(limiter, "enabled", False))
        self.patches.enter_context(patch.object(settings, "CLI_CODE_MODE_ENABLED", True))
        self.api = app

    def bloom_sign_in(self, email):
        user_id = self._run(
            self._add(
                User(email=email, full_name=email, hashed_password=email, role=UserRole.admin)
            )
        )
        user = self._run(self._get(User, user_id))
        token = create_access_token(
            {"sub": str(user.id), "type": "user", "ver": user.session_version}
        )
        return {"Authorization": f"Bearer {token}"}

    def bloom_start_cli_code_session(self, state):
        body = {
            "client_name": self.parameters.CLI_CLIENT_NAME,
            "mode": self.parameters.CLI_CODE_MODE,
            "code_challenge": cli_auth.pkce_challenge(self.parameters.CLI_VERIFIER),
            "state": state,
        }
        return self._run(self._call("POST", self.parameters.CLI_START, body))

    def bloom_cli_approve_body(self, session_id):
        challenge = cli_auth.pkce_challenge(self.parameters.CLI_VERIFIER)
        return {"session_id": session_id, "request_code": cli_auth.request_code(challenge)}

    def bloom_cli_exchange_body(self, session_id, code):
        return {
            "session_id": session_id,
            "code": code,
            "code_verifier": self.parameters.CLI_VERIFIER,
        }

    def bloom_race_cli(self, calls):
        async def race():
            return await asyncio.wait_for(
                asyncio.gather(
                    *(self._call("POST", path, body, headers) for path, body, headers in calls)
                ),
                timeout=self.parameters.RACE_TIMEOUT_SECONDS,
            )

        return self._run(race())

    def bloom_get_cli_session(self, session_id, headers):
        path = self.parameters.CLI_SESSIONS + session_id
        return self._run(self._call("GET", path, None, headers))

    def bloom_cli_exchange(self, session_id, code):
        body = self.bloom_cli_exchange_body(session_id, code)
        return self._run(self._call("POST", self.parameters.CLI_EXCHANGE, body))

    def bloom_refresh_during_revocation(self, email, refresh_token):
        return self._run(self._refresh_during_revocation(email, refresh_token))

    def bloom_seed_campaigns(self, seeds):
        return self._run(self._seed_campaigns(seeds))

    def bloom_seed_public_id_pairs(self, prefixes, suites, campaigns):
        self._run(self._seed_public_id_pairs(prefixes, suites, campaigns))

    def bloom_read_campaign_public_ids(self):
        return self._run(self._read_campaign_public_ids())

    def bloom_read_public_id_shape(self):
        return self._run(self._read_public_id_shape())

    def bloom_try_public_id_inserts(self, prefix, suite_id, campaign_id):
        return self._run(self._try_public_id_inserts(prefix, suite_id, campaign_id))

    def bloom_serve_jira_holding_creation(self, issue):
        searches = []
        both_searched = asyncio.Event()

        async def answer(request):
            if request.url.path.endswith(self.parameters.JIRA_MYSELF):
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"accountId": self.parameters.JIRA_ACCOUNT}
                )
            if request.method == "GET":
                return httpx.Response(self.parameters.STATUS_OK, json={"fields": {}})
            if self.parameters.CREATION_MARK in json.loads(request.content)["jql"]:
                searches.append(True)
                if len(searches) == 2:
                    both_searched.set()
                await asyncio.wait_for(
                    both_searched.wait(), timeout=self.parameters.RACE_HOLD_SECONDS
                )
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"issues": [issue], "isLast": True}
                )
            return httpx.Response(self.parameters.STATUS_OK, json={"issues": [], "isLast": True})

        def client(**kw):
            return REAL_CLIENT(transport=httpx.MockTransport(answer), **kw)

        self.patches.enter_context(patch.object(httpx, "AsyncClient", client))
        return searches

    def bloom_race_sync_now_and_scheduled(self, setting_id, admin_email, now):
        async def sync_now():
            async def pull(db, admin):
                return await integrations.pull_jira_issues(setting_id, db=db, current_user=admin)

            return await self._as_admin(admin_email, pull)

        async def race():
            return await asyncio.wait_for(
                asyncio.gather(sync_now(), integration_sync.run_due(maker=self.maker, now=now)),
                timeout=self.parameters.RACE_TIMEOUT_SECONDS,
            )

        self._run(race())

    async def _create_postgres_database(self):
        admin = create_async_engine(self.pg_admin_url, isolation_level="AUTOCOMMIT")
        async with admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{self.pg_database}"'))
        await admin.dispose()

    async def _drop_postgres_database(self):
        admin = create_async_engine(self.pg_admin_url, isolation_level="AUTOCOMMIT")
        async with admin.connect() as connection:
            await connection.execute(
                text(f'DROP DATABASE IF EXISTS "{self.pg_database}" WITH (FORCE)')
            )
        await admin.dispose()

    async def _call(self, method, path, body=None, headers=None):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.request(
                method, self.parameters.CLI_PREFIX + path, json=body, headers=headers
            )

    async def _fetch_value(self, statement, **values):
        async with self.engine.connect() as connection:
            return (await connection.execute(text(statement), values)).scalar()

    async def _seed_retained_rows(self):
        async with self.engine.begin() as connection:
            user = (
                await connection.execute(
                    text(
                        "INSERT INTO users (email, full_name, hashed_password, role, is_active, "
                        "session_version, created_at, updated_at) VALUES (:email, :name, "
                        "'unused', 'maintainer', true, :version, now(), now()) RETURNING id"
                    ),
                    {
                        "email": self.parameters.RETAINED_EMAIL,
                        "name": self.parameters.RETAINED_NAME,
                        "version": self.parameters.RETAINED_SESSION_VERSION,
                    },
                )
            ).scalar_one()
            project = (
                await connection.execute(
                    text(
                        "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
                        "VALUES (:name, :prefix, 'active', now(), now()) RETURNING id"
                    ),
                    {
                        "name": self.parameters.RETAINED_PROJECT,
                        "prefix": self.parameters.RETAINED_PREFIX,
                    },
                )
            ).scalar_one()
            await connection.execute(
                text(
                    "INSERT INTO user_tokens (user_id, purpose, token_hash, expires_at, "
                    "created_at) VALUES (:user, 'refresh', :digest, now() + interval '1 day', "
                    "now())"
                ),
                {"user": user, "digest": self.parameters.RETAINED_TOKEN_HASH},
            )
            await connection.execute(
                text(
                    "INSERT INTO audit_events (occurred_at, actor_type, actor_user_id, action, "
                    "outcome) VALUES (now(), 'user', :user, 'auth.login', 'success')"
                ),
                {"user": user},
            )
        return {"user": user, "project": project}

    async def _read_retained_rows(self, ids):
        user = ids["user"]
        return {
            "version": await self._fetch_value(
                "SELECT session_version FROM users WHERE id=:user", user=user
            ),
            "project": await self._fetch_value(
                "SELECT name FROM projects WHERE id=:project", project=ids["project"]
            ),
            "token": await self._fetch_value(
                "SELECT token_hash FROM user_tokens WHERE user_id=:user", user=user
            ),
            "audit": await self._fetch_value(
                "SELECT count(*) FROM audit_events WHERE actor_user_id=:user", user=user
            ),
        }

    async def _read_cli_session_table(self):
        exists = await self._fetch_value(
            "SELECT to_regclass('public.cli_auth_sessions') IS NOT NULL"
        )
        if not exists:
            return None
        async with self.engine.connect() as connection:
            columns = (
                await connection.execute(
                    text(
                        "SELECT column_name, is_nullable FROM information_schema.columns "
                        "WHERE table_name='cli_auth_sessions'"
                    )
                )
            ).all()
            indexes = (
                await connection.execute(
                    text("SELECT indexname FROM pg_indexes WHERE tablename='cli_auth_sessions'")
                )
            ).scalars()
            return {
                "columns": {name: nullable == "YES" for name, nullable in columns},
                "indexes": set(indexes),
                "cascade": (
                    await connection.execute(
                        text(
                            "SELECT delete_rule FROM information_schema.referential_constraints "
                            "WHERE constraint_name='cli_auth_sessions_user_id_fkey'"
                        )
                    )
                ).scalar(),
                "check": (
                    await connection.execute(
                        text("SELECT count(*) FROM pg_constraint WHERE conname='ck_cli_auth_mode'")
                    )
                ).scalar(),
                "sessions": (
                    await connection.execute(text("SELECT count(*) FROM cli_auth_sessions"))
                ).scalar(),
            }

    async def _add_cli_sessions(self, user_id):
        challenge = cli_auth.pkce_challenge(self.parameters.CLI_VERIFIER)
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO cli_auth_sessions (id, client_name, mode, code_challenge, state, "
                    "expires_at, created_at) VALUES (:id, :client, :mode, :challenge, :state, "
                    "now() + interval '10 minutes', now())"
                ),
                {
                    "id": uuid.uuid4(),
                    "client": self.parameters.CLI_CLIENT_NAME,
                    "mode": self.parameters.CLI_CODE_MODE,
                    "challenge": challenge,
                    "state": self.parameters.CLI_STATE,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO cli_auth_sessions (id, client_name, mode, redirect_uri, "
                    "code_challenge, state, exchange_code_hash, user_id, "
                    "approved_session_version, expires_at, created_at) VALUES (:id, :client, "
                    ":mode, :uri, :challenge, :state, :digest, :user, :version, "
                    "now() + interval '10 minutes', now())"
                ),
                {
                    "id": uuid.uuid4(),
                    "client": self.parameters.CLI_CLIENT_NAME,
                    "mode": self.parameters.CLI_CALLBACK_MODE,
                    "uri": self.parameters.CLI_CALLBACK_URI,
                    "challenge": challenge,
                    "state": self.parameters.CLI_STATE,
                    "digest": hash_token(self.parameters.CLI_APPROVED_CODE),
                    "user": user_id,
                    "version": self.parameters.RETAINED_SESSION_VERSION,
                },
            )

    async def _insert_project(self, connection, prefix):
        return (
            await connection.execute(
                text(
                    "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
                    "VALUES (:name, :prefix, 'active', now(), now()) RETURNING id"
                ),
                {"name": f"Project {prefix}", "prefix": prefix},
            )
        ).scalar_one()

    async def _insert_campaign(self, connection, project, public_id):
        return (
            await connection.execute(
                text(
                    "INSERT INTO test_campaigns (project_id, campaign_id, name, status, "
                    "visibility, created_at, updated_at) VALUES (:project, :public_id, "
                    "'Demo', 'Planned', 'internal', now(), now()) RETURNING id"
                ),
                {"project": project, "public_id": public_id},
            )
        ).scalar_one()

    async def _insert_suite(self, connection, project, public_id):
        return (
            await connection.execute(
                text(
                    "INSERT INTO test_suites (project_id, suite_id, name, status, visibility, "
                    "created_at, updated_at) VALUES (:project, :public_id, 'Demo', 'Draft', "
                    "'internal', now(), now()) RETURNING id"
                ),
                {"project": project, "public_id": public_id},
            )
        ).scalar_one()

    async def _seed_campaigns(self, seeds):
        ids = {}
        async with self.engine.begin() as connection:
            for prefix, public_ids in seeds.items():
                project = await self._insert_project(connection, prefix)
                ids[prefix] = [
                    await self._insert_campaign(connection, project, public_id)
                    for public_id in public_ids
                ]
        return ids

    async def _seed_public_id_pairs(self, prefixes, suites, campaigns):
        async with self.engine.begin() as connection:
            for prefix, suite_id, campaign_id in zip(prefixes, suites, campaigns):
                project = await self._insert_project(connection, prefix)
                if suite_id:
                    await self._insert_suite(connection, project, suite_id)
                if campaign_id:
                    await self._insert_campaign(connection, project, campaign_id)

    async def _read_campaign_public_ids(self):
        async with self.engine.connect() as connection:
            rows = await connection.execute(text("SELECT id, campaign_id FROM test_campaigns"))
            return dict(rows.all())

    async def _read_public_id_shape(self):
        async with self.engine.connect() as connection:
            nullable = (
                await connection.execute(
                    text(
                        "SELECT is_nullable FROM information_schema.columns "
                        "WHERE table_name = 'test_campaigns' AND column_name = 'campaign_id'"
                    )
                )
            ).scalar()
            indexes = (
                await connection.execute(
                    text("SELECT indexname FROM pg_indexes WHERE indexname IN :names").bindparams(
                        bindparam("names", expanding=True)
                    ),
                    {"names": self.parameters.PUBLIC_ID_INDEXES},
                )
            ).scalars()
            revision = (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar()
            return {"nullable": nullable, "indexes": sorted(indexes), "revision": revision}

    async def _try_public_id_inserts(self, prefix, suite_id, campaign_id):
        states = []
        async with self.engine.connect() as connection:
            project = (
                await connection.execute(
                    text("SELECT id FROM projects WHERE prefix = :prefix"), {"prefix": prefix}
                )
            ).scalar_one()
            await self._insert_suite(connection, project, suite_id)
            await connection.commit()
            attempts = (
                (self._insert_suite, suite_id),
                (self._insert_campaign, campaign_id),
                (self._insert_campaign, None),
            )
            for insert, public_id in attempts:
                try:
                    await insert(connection, project, public_id)
                    await connection.commit()
                    states.append(None)
                except IntegrityError as exc:
                    await connection.rollback()
                    states.append(getattr(exc.orig, "sqlstate", None))
        return states

    async def _refresh_during_revocation(self, email, refresh_token):
        asked_for_lock = asyncio.Event()

        def watch(conn, cursor, statement, parameters, context, executemany):
            if "FROM users" in statement and "FOR " in statement:
                asked_for_lock.set()

        async with self.maker() as seed:
            user = User(email=email, full_name=email, hashed_password=email, is_active=True)
            seed.add(user)
            await seed.flush()
            user_id = user.id
            await seed.execute(
                text(
                    "INSERT INTO user_tokens (user_id, purpose, token_hash, expires_at, "
                    "created_at) VALUES (:user, 'refresh', :digest, now() + interval '1 day', "
                    "now())"
                ),
                {"user": user_id, "digest": hash_token(refresh_token)},
            )
            await seed.commit()

        async def refresh():
            async with self.maker() as request:
                try:
                    await cli_auth.refresh_credentials(request, refresh_token)
                    await request.commit()
                    return None
                except cli_auth.CliAuthorizationError as exc:
                    await request.rollback()
                    return exc.reason

        event.listen(self.engine.sync_engine, "before_cursor_execute", watch)
        try:
            async with self.maker() as revoker:
                account = await revoker.scalar(
                    select(User).where(User.id == user_id).with_for_update()
                )
                task = asyncio.create_task(refresh())
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        asked_for_lock.wait(), self.parameters.CLI_LOCK_WAIT_SECONDS
                    )
                waited = asked_for_lock.is_set()
                await revoker.execute(
                    text(f"SET LOCAL lock_timeout='{self.parameters.CLI_LOCK_TIMEOUT}'")
                )
                account.session_version += 1
                await invalidate_all_refresh_tokens(revoker, user_id)
                await revoker.commit()
                reason = await asyncio.wait_for(task, self.parameters.CLI_LOCK_WAIT_SECONDS)
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", watch)
        return SimpleNamespace(waited=waited, reason=reason)
