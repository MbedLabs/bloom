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
import importlib.util
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import httpx
from fastapi import Depends, FastAPI
from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
    bindparam,
    event,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main
from app.api import auth as auth_api
from app.api import cli_auth as cli_auth_api
from app.api import integrations
from app.api import users as users_api
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import limiter
from app.core.id_generator import next_doc_id
from app.core.link_rules import allowed_link_triples
from app.core.security import create_access_token, get_current_user
from app.models import (
    ArtefactComment,
    ArtefactWorkflow,
    AuditEvent,
    Project,
    Requirement,
)
from app.models import TestCase as TestCaseModel
from app.models.cli_auth_session import CliAuthSession
from app.models.user import User, UserRole
from app.models.workflow import (
    ArtefactRequest,
    ArtefactRequestRecipient,
    ArtefactRevision,
    ArtefactRevisionFile,
)
from app.services import cli_auth, integration_sync
from app.services.token_service import hash_token, invalidate_all_refresh_tokens
from app.tools.check_link_rules import check_link_rules
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

    def bloom_start_main_api(self):
        self.patches.enter_context(patch.dict(main.app.dependency_overrides))
        main.app.dependency_overrides[get_db] = self._serve_session
        self.patches.enter_context(patch.object(limiter, "enabled", False))
        self.api = main.app

    def bloom_add_conflicting_route(self):
        routes = list(main.app.router.routes)
        letter = self.parameters.CONFLICT_PREFIX_LETTER

        @main.app.post(self.parameters.CONFLICT_PATH, name=self.parameters.CONFLICT_ROUTE_NAME)
        async def flush_conflict(db=Depends(get_db)):
            prefix = f"{letter}{uuid.uuid4().hex[:5].upper()}"
            db.add(Project(name=f"first {prefix}", prefix=prefix))
            db.add(Project(name=f"second {prefix}", prefix=prefix))
            await db.flush()

        self.patches.callback(setattr, main.app.router, "routes", routes)

    def bloom_api_post(self, path):
        answer = self._run(self._send("POST", path))
        try:
            body = answer.json()
        except ValueError:
            body = None
        return SimpleNamespace(status=answer.status_code, body=body, text=answer.text)

    def bloom_log_in_for_cookie(self, email, password):
        body = {"email": email, "password": password}
        return self._session_answer(self._run(self._send("POST", "/api/auth/login", json=body)))

    def bloom_refresh(self, cookie=None):
        return self._session_answer(
            self._run(self._send("POST", "/api/auth/refresh", cookie=cookie))
        )

    def bloom_log_out(self, cookie):
        return self._session_answer(
            self._run(self._send("POST", "/api/auth/logout", cookie=cookie))
        )

    def bloom_read_account(self, token):
        headers = {"Authorization": f"Bearer {token}"}
        answer = self._run(self._send("GET", "/api/auth/me", headers=headers))
        return SimpleNamespace(status=answer.status_code, body=answer.json())

    def bloom_change_password(self, token, current, new):
        headers = {"Authorization": f"Bearer {token}"}
        body = {"current_password": current, "new_password": new}
        answer = self._run(self._send("PUT", "/api/auth/me/password", json=body, headers=headers))
        return answer.status_code

    def bloom_request_password_reset(self, email):
        return self._mailed_token(
            auth_api,
            "send_password_reset_email",
            "reset_link",
            self._send("POST", "/api/auth/forgot-password", json={"email": email}),
        )

    def bloom_invite(self, admin_token, email, role):
        headers = {"Authorization": f"Bearer {admin_token}"}
        body = {"email": email, "full_name": email, "role": role}
        return self._mailed_token(
            users_api,
            "send_invite_email",
            "invite_link",
            self._send("POST", "/api/users/invite", json=body, headers=headers),
        )

    def bloom_request_verification(self, token):
        headers = {"Authorization": f"Bearer {token}"}
        return self._mailed_token(
            auth_api,
            "send_verification_email",
            "verification_link",
            self._send("POST", "/api/auth/resend-verification", headers=headers),
        )

    def bloom_race_requests(self, path, json=None, cookie=None):
        async def race():
            sends = [
                self._send("POST", path, json=json, cookie=cookie)
                for _ in range(self.parameters.TOKEN_RACE_USES)
            ]
            return [answer.status_code for answer in await asyncio.gather(*sends)]

        return self._run(race())

    def bloom_act_as(self, user_id):
        user = self._run(self._get(User, user_id))

        async def actor():
            return user

        main.app.dependency_overrides[get_current_user] = actor

    def bloom_race_first_workflow_reads(self, requirement_id):
        return self._run(self._race_first_workflow_reads(requirement_id))

    def bloom_read_workflow(self, requirement_id):
        path = self.parameters.WORKFLOW_RACE_PATH.format(id=requirement_id)
        answer = self._run(self._send("GET", path))
        return SimpleNamespace(status=answer.status_code, body=answer.json())

    def bloom_list_workflows(self):
        return self._run(self._all(select(ArtefactWorkflow).order_by(ArtefactWorkflow.id)))

    def bloom_reset_password(self, token, new):
        body = {"token": token, "new_password": new}
        return self._run(self._send("POST", "/api/auth/reset-password", json=body)).status_code

    def bloom_probe_sessions(self, login, email, old_password, new_password):
        return SimpleNamespace(
            account=self.bloom_read_account(login.access_token).status,
            refresh=self.bloom_refresh(login.cookie).status,
            old_password=self.bloom_log_in_for_cookie(email, old_password).status,
            new_password=self.bloom_log_in_for_cookie(email, new_password).status,
        )

    def bloom_seed_requirements(self, prefix, req_ids):
        return self._run(self._seed_requirements(prefix, req_ids))

    def bloom_insert_link(self, project, source, target, role, ends, keep=True):
        return self._run(self._insert_link(project, source, target, role, ends, keep))

    def bloom_insert_legacy_requirement_link(self):
        self._run(
            self._execute(
                "INSERT INTO requirement_links (source_id, target_id, link_type, created_at) "
                "VALUES (1, 2, :link_type, now())",
                link_type=self.parameters.LINK_LEGACY[0],
            )
        )

    def bloom_link_constraint_validated(self):
        return self._run(
            self._fetch_value(
                "SELECT convalidated FROM pg_constraint WHERE conname = :constraint "
                "AND conrelid = 'artefact_links'::regclass",
                constraint=self.parameters.LINK_CONSTRAINT,
            )
        )

    def bloom_first_link_id(self):
        return self._run(self._fetch_value("SELECT id FROM artefact_links ORDER BY id"))

    def bloom_set_link_role(self, link_id, role):
        self._run(
            self._execute(
                "UPDATE artefact_links SET role = :role WHERE id = :id", role=role, id=link_id
            )
        )

    def bloom_count_links(self):
        return (
            self._run(self._fetch_value("SELECT count(*) FROM requirement_links")),
            self._run(self._fetch_value("SELECT count(*) FROM artefact_links")),
        )

    def bloom_check_link_rules(self):
        return self._run(self._check_link_rules())

    def bloom_read_allowed_link_triples(self):
        return self._run(self._read_allowed_link_triples())

    def bloom_code_link_triples(self):
        return set(allowed_link_triples())

    def bloom_seed_legacy_rows(self, project):
        self._run(self._seed_legacy_rows(project))

    def bloom_read_legacy_rows(self, workflows=False):
        return self._run(self._read_legacy_rows(workflows))

    def bloom_compare_workflow_schema(self):
        return self._run(self._compare_workflow_schema())

    def bloom_request_email_change(self, token, password, new_email):
        body = {"current_password": password, "new_email": new_email}
        return self._mail_call("POST", "/api/auth/me/email", token, body)

    def bloom_confirm_email_change(self, token):
        return self._mail_call("POST", "/api/auth/confirm-email-change", json={"token": token})

    def bloom_approve_email_change(self, admin_token, user_id):
        return self._mail_call("POST", f"/api/users/{user_id}/email/approve", admin_token)

    def bloom_start_email_change_for(self, admin_token, user_id, new_email):
        body = {"new_email": new_email}
        return self._mail_call("POST", f"/api/users/{user_id}/email", admin_token, body)

    def bloom_update_account_email(self, admin_token, user_id, email):
        return self._mail_call("PATCH", f"/api/users/{user_id}", admin_token, {"email": email})

    def bloom_send_invitation(self, admin_token, email, role):
        body = {"email": email, "full_name": email, "role": role}
        return self._mail_call("POST", "/api/users/invite", admin_token, body)

    def bloom_accept_invitation(self, token, password):
        body = {"token": token, "password": password}
        return self._mail_call("POST", "/api/auth/accept-invite", json=body)

    def bloom_mail_token(self, mail):
        link = mail.get("confirm_link") or mail.get("invite_link") or ""
        found = re.search(r"token=([^&\s]+)", link)
        return found.group(1) if found else None

    def bloom_set_pending_email(self, user_id, email):
        self._run(
            self._execute(
                "UPDATE users SET pending_email = :email WHERE id = :id", email=email, id=user_id
            )
        )

    def bloom_probe_email_sessions(self, login, old_email, new_email, password):
        return (
            self.bloom_read_account(login.access_token).status,
            self.bloom_refresh(login.cookie).status,
            self.bloom_log_in_for_cookie(old_email, password).status,
            self.bloom_log_in_for_cookie(new_email, password).status,
        )

    def bloom_seed_overlap_entries(self):
        return self._run(self._pg(self._seed_overlap_entries))

    def bloom_snapshot_project_access(self):
        return self._run(self._pg(self._snapshot_project_access))

    def bloom_add_overlapping_group(self, seeded):
        async def work(connection):
            return await self._add_overlapping_group(connection, seeded)

        return self._run(self._pg(work))

    def bloom_delete_access_entry(self, entry):
        async def work(connection):
            await connection.execute("DELETE FROM project_access WHERE id = $1", entry)

        self._run(self._pg(work))

    def bloom_seed_visions_holders(self):
        return self._run(self._pg(self._seed_visions_holders))

    def bloom_read_visions_state(self, seeded):
        async def work(connection):
            return await self._read_visions_state(connection, seeded)

        return self._run(self._pg(work))

    def bloom_add_vision(self, project):
        async def work(connection):
            return await connection.fetchval(
                "INSERT INTO documents (project_id, doc_id, doc_type, title, status, version, "
                "visibility, created_at, updated_at) VALUES ($1, $2, $3, $2, 'Draft', '1', "
                "'internal', now(), now()) RETURNING id",
                project,
                self.parameters.VISIONS_DOC_ID,
                self.parameters.VISIONS_KIND,
            )

        return self._run(self._pg(work))

    def bloom_delete_document(self, document):
        async def work(connection):
            await connection.execute("DELETE FROM documents WHERE id = $1", document)

        self._run(self._pg(work))

    def bloom_seed_workflow_of_a_creator(self):
        return self._run(self._seed_workflow_of_a_creator())

    def bloom_read_workflow_assignees(self):
        return self._run(self._read_workflow_assignees())

    def bloom_seed_requirement_with_parent(self, prefix, req_ids):
        self._run(self._seed_requirement_with_parent(prefix, req_ids))

    def bloom_read_requirement_parent_state(self):
        return self._run(self._read_requirement_parent_state())

    def bloom_add_requirements(self, project_id, req_ids, created_by_id=None):
        return [
            self._run(
                self._add(
                    Requirement(
                        project_id=project_id,
                        req_id=req_id,
                        title=req_id,
                        status=self.parameters.STATUS_DRAFT,
                        created_by_id=created_by_id,
                    )
                )
            )
            for req_id in req_ids
        ]

    def bloom_add_test_case(self, project_id, tc_id, title):
        return self._run(self._add(TestCaseModel(project_id=project_id, tc_id=tc_id, title=title)))

    def bloom_next_requirement_id(self, project_id, prefix):
        return self._run(self._next_requirement_id(project_id, prefix))

    def bloom_list_requirement_ids(self, project_id):
        query = select(Requirement.req_id).where(Requirement.project_id == project_id)
        return self._run(self._all(query.order_by(Requirement.req_id)))

    def bloom_list_test_case_ids(self):
        return self._run(self._all(select(TestCaseModel.tc_id)))

    def bloom_repair_pre_baseline_schema(self):
        return self._run(self._repair_pre_baseline_schema())

    def bloom_burst_forged_requests(self):
        return self._run(self._burst_forged_requests())

    def bloom_count_audit_events(self, action, ip, outcome=None):
        query = select(func.count(AuditEvent.id)).where(
            AuditEvent.action == action, AuditEvent.ip == ip
        )
        if outcome:
            query = query.where(AuditEvent.outcome == outcome)
        return self._run(self._scalar(query))

    def bloom_refusal_threshold(self):
        return settings.AUDIT_REFUSAL_THRESHOLD

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

    def bloom_seed_requirement_texts(self, prefix, rows):
        self._run(self._seed_requirement_texts(prefix, rows))

    def bloom_read_requirement_texts(self):
        return self._run(self._read_requirement_texts())

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

    async def _send(self, method, path, json=None, headers=None, cookie=None):
        headers = dict(headers or {})
        if cookie:
            headers["Cookie"] = f"{self.parameters.REFRESH_COOKIE}={cookie}"
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.request(method, path, json=json, headers=headers)

    def _session_answer(self, answer):
        name = f"{self.parameters.REFRESH_COOKIE}="
        header = next((h for h in answer.headers.get_list("set-cookie") if h.startswith(name)), "")
        try:
            body = answer.json()
        except ValueError:
            body = None
        return SimpleNamespace(
            status=answer.status_code,
            body=body,
            set_cookie=header,
            cookie=header[len(name) :].split(";")[0] or None,
            access_token=body.get("access_token") if isinstance(body, dict) else None,
        )

    def _mail_call(self, method, path, token=None, json=None):
        mails = []
        headers = {"Authorization": f"Bearer {token}"} if token else None
        senders = (
            (auth_api, self.parameters.EMAIL_AUTHORIZATION_SENDER),
            (auth_api, self.parameters.EMAIL_CHANGE_SENDER),
            (users_api, self.parameters.EMAIL_CHANGE_SENDER),
            (users_api, self.parameters.EMAIL_INVITE_SENDER),
        )

        def recorder(sender):
            return lambda **mail: mails.append({self.parameters.EMAIL_SENDER_KEY: sender, **mail})

        with contextlib.ExitStack() as stack:
            for module, sender in senders:
                stack.enter_context(patch.object(module, sender, recorder(sender)))
            answer = self._run(self._send(method, path, json=json, headers=headers))
        try:
            body = answer.json()
        except ValueError:
            body = None
        return SimpleNamespace(status=answer.status_code, body=body, mails=mails)

    def _mailed_token(self, module, sender, link, request):
        captured = {}
        with patch.object(module, sender, lambda **mail: captured.update(link=mail[link])):
            answer = self._run(request)
        found = re.search(r"token=([^&\s]+)", captured.get("link", ""))
        return SimpleNamespace(status=answer.status_code, token=found.group(1) if found else None)

    async def _race_first_workflow_reads(self, requirement_id):
        arrived = asyncio.Event()
        lookups = []
        execute = AsyncSession.execute

        async def held_execute(session, statement, *args, **kwargs):
            result = await execute(session, statement, *args, **kwargs)
            first_lookup = (
                session.info.get("racing")
                and str(statement).startswith(self.parameters.WORKFLOW_RACE_LOOKUP)
                and len(lookups) < 2
            )
            if first_lookup:
                lookups.append(statement)
                if len(lookups) == 2:
                    arrived.set()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(arrived.wait(), self.parameters.WORKFLOW_RACE_WAIT)
            return result

        async def racing_session():
            async with self.maker() as session:
                session.info["racing"] = True
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        path = self.parameters.WORKFLOW_RACE_PATH.format(id=requirement_id)
        transport = httpx.ASGITransport(app=self.api)
        with (
            patch.dict(main.app.dependency_overrides, {get_db: racing_session}),
            patch.object(AsyncSession, "execute", held_execute),
        ):
            async with REAL_CLIENT(
                transport=transport, base_url=self.parameters.API_BASE
            ) as client:
                replies = await asyncio.wait_for(
                    asyncio.gather(client.get(path), client.get(path)),
                    self.parameters.RACE_TIMEOUT_SECONDS,
                )
        return [SimpleNamespace(status=reply.status_code, body=reply.json()) for reply in replies]

    async def _pg(self, work):
        dsn = self.pg_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        connection = await asyncpg.connect(dsn)
        try:
            return await work(connection)
        finally:
            await connection.close()

    async def _insert_person(self, connection, email):
        return await connection.fetchval(
            "INSERT INTO users (email, full_name, hashed_password, role, is_active, created_at, "
            "updated_at) VALUES ($1, $1, 'x', 'maintainer', true, now(), now()) RETURNING id",
            email,
        )

    async def _seed_overlap_entries(self, connection):
        project = await connection.fetchval(
            "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
            "VALUES ($1, $1, 'active', now(), now()) RETURNING id",
            self.parameters.OVERLAP_PREFIX,
        )
        people = [
            await self._insert_person(connection, email) for email in self.parameters.OVERLAP_PEOPLE
        ]
        groups = dict(await connection.fetch("SELECT name, id FROM groups"))
        policy = await connection.fetchval(
            "SELECT id FROM policies WHERE name = $1", self.parameters.OVERLAP_POLICY
        )
        for index, person in enumerate(people):
            entry = await connection.fetchval(
                "INSERT INTO project_access (project_id, user_id, owner, inherit_policies, "
                "policy_group_id, created_at) VALUES ($1, $2, $3, $4, $5, now()) RETURNING id",
                project,
                person,
                index == 0,
                index == 1,
                groups[self.parameters.OVERLAP_BUNDLE] if index == 3 else None,
            )
            if index == 2:
                await connection.execute(
                    "INSERT INTO project_access_policies VALUES ($1, $2)", entry, policy
                )
        await connection.execute(
            "INSERT INTO project_access (project_id, group_id, owner, inherit_policies, "
            "created_at) VALUES ($1, $2, false, true, now())",
            project,
            groups[self.parameters.OVERLAP_SECOND_BUNDLE],
        )
        return SimpleNamespace(project=project, people=people, groups=groups)

    async def _snapshot_project_access(self, connection):
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
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE tablename = 'project_access' ORDER BY indexname"
                )
            ],
            "revision": await connection.fetchval("SELECT version_num FROM alembic_version"),
        }

    async def _add_overlapping_group(self, connection, seeded):
        statement = (
            "INSERT INTO project_access (project_id, user_id, policy_group_id, owner, "
            "inherit_policies, created_at) VALUES ($1, $2, $3, false, false, now()) RETURNING id"
        )
        second = seeded.groups[self.parameters.OVERLAP_SECOND_BUNDLE]

        async def refused(person, group):
            try:
                await connection.fetchval(statement, seeded.project, person, group)
            except asyncpg.UniqueViolationError:
                return True
            return False

        entry = await connection.fetchval(statement, seeded.project, seeded.people[3], second)
        return SimpleNamespace(
            entry=entry,
            duplicate_refused=await refused(seeded.people[3], second),
            plain_refused=await refused(seeded.people[0], None),
        )

    async def _seed_visions_holders(self, connection):
        ids = dict(await connection.fetch("SELECT name, id FROM policies"))
        project = await connection.fetchval(
            "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
            "VALUES ($1, $1, 'Active', now(), now()) RETURNING id",
            self.parameters.VISIONS_PREFIX,
        )
        seeded = {"project": project}
        held = {
            "released": self.parameters.VISIONS_RELEASED_SET,
            "spec_only": (self.parameters.VISIONS_SPEC_POLICY,),
        }
        for key, names in held.items():
            user = await self._insert_person(connection, self.parameters.VISIONS_HOLDERS[key])
            entry = await connection.fetchval(
                "INSERT INTO project_access (project_id, user_id, owner, inherit_policies, "
                "created_at) VALUES ($1, $2, false, false, now()) RETURNING id",
                project,
                user,
            )
            for name in names:
                await connection.execute(
                    "INSERT INTO project_access_policies (access_id, policy_id) VALUES ($1, $2)",
                    entry,
                    ids[name],
                )
            seeded[key] = entry
        seeded["group"] = await connection.fetchval(
            "INSERT INTO groups (name, description, created_at, updated_at) "
            "VALUES ($1, '', now(), now()) RETURNING id",
            self.parameters.VISIONS_GROUP,
        )
        await connection.execute(
            "INSERT INTO group_policies (group_id, policy_id) VALUES ($1, $2)",
            seeded["group"],
            ids[self.parameters.VISIONS_SPEC_POLICY],
        )
        kind = self.parameters.VISIONS_SPEC_KIND
        seeded["editable"] = await connection.fetchval(
            "INSERT INTO policies (name, description, scope, permissions, type_tags, is_default, "
            "created_at, updated_at) VALUES ($1, '', 'document', $2, $3, false, now(), now()) "
            "RETURNING id",
            self.parameters.VISIONS_EDITABLE,
            json.dumps({kind: ["comment", "view"]}),
            json.dumps({kind: {"all": True, "visibility": [], "tags": []}}),
        )
        return seeded

    async def _read_visions_state(self, connection, seeded):
        async def entry_policies(entry):
            rows = await connection.fetch(
                "SELECT p.name FROM policies p JOIN project_access_policies x "
                "ON x.policy_id = p.id WHERE x.access_id = $1 ORDER BY p.name",
                entry,
            )
            return [row["name"] for row in rows]

        async def group_policies(group):
            rows = await connection.fetch(
                "SELECT p.name FROM policies p JOIN group_policies x ON x.policy_id = p.id "
                "JOIN groups g ON g.id = x.group_id WHERE g.name = $1 ORDER BY p.name",
                group,
            )
            return [row["name"] for row in rows]

        editable = await connection.fetch(
            "SELECT row_to_json(p)::text AS row FROM policies p WHERE id = $1", seeded["editable"]
        )
        group = await connection.fetch(
            "SELECT row_to_json(g)::text AS row FROM groups g WHERE id = $1", seeded["group"]
        )
        covered = await connection.fetch(
            "SELECT name, permissions::text AS permissions, type_tags::text AS type_tags "
            "FROM policies WHERE is_default AND name = ANY($1::text[])",
            list(self.parameters.VISIONS_COVERED),
        )
        visions = await connection.fetch(
            "SELECT scope, is_default FROM policies WHERE name = $1", self.parameters.VISIONS_POLICY
        )
        return {
            "released": await entry_policies(seeded["released"]),
            "spec_only": await entry_policies(seeded["spec_only"]),
            "group": await group_policies(self.parameters.VISIONS_GROUP),
            "product_owners": await group_policies(self.parameters.VISIONS_OWNERS),
            "editable": [row["row"] for row in editable],
            "group_row": [row["row"] for row in group],
            "covered": {
                row["name"]: (json.loads(row["permissions"]), json.loads(row["type_tags"]))
                for row in covered
            },
            "visions": [tuple(row) for row in visions],
        }

    async def _execute(self, statement, **values):
        async with self.engine.begin() as connection:
            await connection.execute(text(statement), values)

    async def _seed_requirements(self, prefix, req_ids):
        statement = (
            "INSERT INTO requirements (project_id, req_id, title, status, priority, req_type, "
            "req_origin, visibility, created_at, updated_at) VALUES (:project, :req_id, :req_id, "
            "'Draft', 'Medium', 'Functional', 'Internal', 'internal', now(), now())"
        )
        async with self.engine.begin() as connection:
            project = await self._insert_project(connection, prefix)
            for req_id in req_ids:
                await connection.execute(text(statement), {"project": project, "req_id": req_id})
        return project

    async def _insert_link(self, project, source, target, role, ends, keep):
        statement = text(
            "INSERT INTO artefact_links (project_id, source_type, source_id, target_type, "
            "target_id, role, suspect, created_at) "
            "VALUES (:project, :source, :source_id, :target, :target_id, :role, false, now()) "
            "RETURNING id"
        )
        values = {"project": project, "source": source, "target": target, "role": role}
        values["source_id"], values["target_id"] = ends
        async with self.engine.connect() as connection:
            transaction = await connection.begin()
            try:
                link_id = (await connection.execute(statement, values)).scalar_one()
            except IntegrityError as error:
                await transaction.rollback()
                return SimpleNamespace(id=None, error=str(error))
            if keep:
                await transaction.commit()
            else:
                await transaction.rollback()
            return SimpleNamespace(id=link_id, error=None)

    async def _check_link_rules(self):
        lines = []
        async with self.maker() as db:
            exit_code = await check_link_rules(db, validate=True, emit=lines.append)
            await db.commit()
        return SimpleNamespace(exit_code=exit_code, report=[json.loads(line) for line in lines])

    async def _read_allowed_link_triples(self):
        async with self.engine.connect() as connection:
            rows = await connection.execute(
                text("SELECT source_type, target_type, role FROM allowed_link_triples")
            )
            return {tuple(row) for row in rows}

    async def _seed_legacy_rows(self, project):
        await self._execute(
            "UPDATE requirements SET status = :status WHERE id = 1",
            status=self.parameters.LEGACY_REQUIREMENT_STATUS,
        )
        await self._execute(
            "INSERT INTO change_requests (project_id, change_id, title, status, visibility, "
            "priority, change_type, created_at, updated_at) VALUES (:project, :change_id, "
            ":change_id, :status, 'internal', 'Medium', 'Enhancement', now(), now())",
            project=project,
            change_id=self.parameters.LEGACY_CHANGE_ID,
            status=self.parameters.LEGACY_CHANGE_STATUS,
        )
        await self._execute(
            "INSERT INTO baselines (project_id, name, status, baseline_type, snapshot, "
            "created_at, updated_at) VALUES (:project, :name, 'Open', 'Milestone', "
            "CAST(:snapshot AS JSON), now(), now())",
            project=project,
            name=self.parameters.LEGACY_BASELINE_NAME,
            snapshot=self.parameters.LEGACY_SNAPSHOT,
        )

    async def _read_legacy_rows(self, workflows):
        async with self.engine.connect() as connection:
            rows = await connection.execute(text("SELECT id, status FROM requirements ORDER BY id"))
            requirements = [tuple(row) for row in rows]
        counts = None
        if workflows:
            counts = [
                await self._fetch_value("SELECT count(*) FROM artefact_workflows"),
                await self._fetch_value("SELECT count(*) FROM artefact_revisions"),
                await self._fetch_value("SELECT count(*) FROM artefact_requests"),
            ]
        return SimpleNamespace(
            requirements=requirements,
            change=await self._fetch_value("SELECT status FROM change_requests"),
            baseline=await self._fetch_value("SELECT snapshot::text FROM baselines"),
            workflows=counts,
        )

    async def _compare_workflow_schema(self):
        async with self.engine.connect() as connection:
            return await connection.run_sync(self._workflow_schema_mismatches)

    def _workflow_schema_mismatches(self, connection):
        inspector = inspect(connection)
        found = {aspect: [] for aspect in self.parameters.WORKFLOW_SCHEMA_ASPECTS}
        compared = dict.fromkeys(found, 0)
        quoted = r"'([^']*)'"

        def note(aspect, where, actual, expected):
            compared[aspect] += 1
            if actual != expected:
                found[aspect].append(f"{where}: {actual!r} is not {expected!r}")

        def kind(column_type):
            return str(column_type.compile(dialect=connection.dialect)).upper()

        models = (
            ArtefactWorkflow,
            ArtefactRevision,
            ArtefactRequest,
            ArtefactRequestRecipient,
            ArtefactRevisionFile,
        )
        for table in (model.__table__ for model in models):
            columns = inspector.get_columns(table.name)
            note(
                "columns",
                table.name,
                sorted(column["name"] for column in columns),
                sorted(table.columns.keys()),
            )
            for column in columns:
                if column["name"] in table.c:
                    expected = table.c[column["name"]]
                    note(
                        "types",
                        f"{table.name}.{column['name']}",
                        (column["nullable"], kind(column["type"])),
                        (expected.nullable, kind(expected.type)),
                    )
            note(
                "primary",
                table.name,
                inspector.get_pk_constraint(table.name)["constrained_columns"],
                [column.name for column in table.primary_key],
            )
            note(
                "unique",
                table.name,
                sorted(
                    tuple(u["column_names"]) for u in inspector.get_unique_constraints(table.name)
                ),
                sorted(
                    tuple(column.name for column in constraint.columns)
                    for constraint in table.constraints
                    if type(constraint) is UniqueConstraint
                ),
            )
            note(
                "foreign",
                table.name,
                sorted(
                    (
                        (
                            tuple(key["constrained_columns"]),
                            tuple(f"{key['referred_table']}.{c}" for c in key["referred_columns"]),
                            key["options"].get("ondelete"),
                        )
                        for key in inspector.get_foreign_keys(table.name)
                    ),
                    key=repr,
                ),
                sorted(
                    (
                        (
                            tuple(column.name for column in constraint.columns),
                            tuple(element.target_fullname for element in constraint.elements),
                            constraint.ondelete,
                        )
                        for constraint in table.foreign_key_constraints
                    ),
                    key=repr,
                ),
            )
            checks = inspector.get_check_constraints(table.name)
            expected_checks = {
                constraint.name: str(constraint.sqltext)
                for constraint in table.constraints
                if type(constraint) is CheckConstraint
            }
            note("checks", table.name, sorted(c["name"] for c in checks), sorted(expected_checks))
            for check in checks:
                sqltext = expected_checks.get(check["name"])
                if sqltext is not None:
                    note(
                        "checks",
                        f"{check['name']} values",
                        re.findall(quoted, check["sqltext"]),
                        re.findall(quoted, sqltext),
                    )
                    field = sqltext.split()[0]
                    note(
                        "checks",
                        f"{check['name']} on {field}",
                        bool(re.search(rf"\b{field}\b", check["sqltext"])),
                        True,
                    )
        pending = next(
            (
                index
                for index in inspector.get_indexes(ArtefactRequest.__table__.name)
                if index["name"] == self.parameters.WORKFLOW_PENDING_INDEX
            ),
            None,
        )
        actual = None
        if pending is not None:
            predicate = re.sub(
                r"::[a-z ]+", "", str(pending["dialect_options"]["postgresql_where"])
            )
            actual = (pending["unique"], pending["column_names"], re.sub(r"[()\s]", "", predicate))
        note(
            "pending",
            self.parameters.WORKFLOW_PENDING_INDEX,
            actual,
            (
                True,
                self.parameters.WORKFLOW_PENDING_COLUMNS,
                self.parameters.WORKFLOW_PENDING_WHERE,
            ),
        )
        comment = ArtefactComment.__table__
        stored = {column["name"]: column for column in inspector.get_columns(comment.name)}
        for name in self.parameters.WORKFLOW_COMMENT_COLUMNS:
            column = stored.get(name)
            note(
                "comments",
                f"{comment.name}.{name}",
                None if column is None else (column["nullable"], kind(column["type"])),
                (True, kind(comment.c[name].type)),
            )
        keys = [
            (key["constrained_columns"], key["referred_table"], key["options"].get("ondelete"))
            for key in inspector.get_foreign_keys(comment.name)
        ]
        note("comments", "review request key", self.parameters.WORKFLOW_COMMENT_KEY in keys, True)
        return SimpleNamespace(found=found, compared=compared)

    async def _next_requirement_id(self, project_id, prefix):
        async with self.maker() as db:
            new_id = await next_doc_id(
                db,
                Requirement,
                Requirement.req_id,
                project_id,
                prefix,
                self.parameters.WIDENING_KIND,
            )
            await db.commit()
            return new_id

    async def _seed_workflow_of_a_creator(self):
        async with self.engine.begin() as connection:
            project = await self._insert_project(connection, self.parameters.ASSIGNEE_PREFIX)
            person = (
                await connection.execute(
                    text(
                        "INSERT INTO users (email, full_name, hashed_password, role, is_active, "
                        "created_at, updated_at) VALUES (:email, :email, 'x', 'maintainer', true, "
                        "now(), now()) RETURNING id"
                    ),
                    {"email": self.parameters.ASSIGNEE_EMAIL},
                )
            ).scalar_one()
            await connection.execute(
                text(
                    "INSERT INTO artefact_workflows (project_id, artefact_type, artefact_id, "
                    "revision_number, revision_creator_id, phase) "
                    "VALUES (:project, 'requirement', 1, 1, :person, 'Draft')"
                ),
                {"project": project, "person": person},
            )
        return person

    async def _read_workflow_assignees(self):
        async with self.engine.connect() as connection:
            rows = await connection.execute(
                text("SELECT revision_creator_id, assignee_id FROM artefact_workflows ORDER BY id")
            )
            return [tuple(row) for row in rows]

    async def _seed_requirement_with_parent(self, prefix, req_ids):
        statement = (
            "INSERT INTO requirements (project_id, parent_id, req_id, title, status, priority, "
            "req_type, req_origin, visibility, created_at, updated_at) VALUES (:project, :parent, "
            ":req_id, :req_id, 'Draft', 'Medium', 'Functional', 'Internal', 'internal', now(), "
            "now()) RETURNING id"
        )
        async with self.engine.begin() as connection:
            project = await self._insert_project(connection, prefix)
            parent = None
            for req_id in req_ids:
                values = {"project": project, "parent": parent, "req_id": req_id}
                parent = (await connection.execute(text(statement), values)).scalar_one()

    async def _read_requirement_parent_state(self):
        async with self.engine.connect() as connection:
            rows = await connection.execute(text("SELECT req_id FROM requirements ORDER BY req_id"))
            req_ids = [row[0] for row in rows]
        has_parent = await self._fetch_value(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'requirements' AND column_name = 'parent_id')"
        )
        return req_ids, has_parent

    async def _repair_pre_baseline_schema(self):
        path = ROOT / "alembic" / "versions" / self.parameters.REPAIR_MIGRATION
        spec = importlib.util.spec_from_file_location(path.stem, path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        async with self.engine.begin() as connection:
            await connection.exec_driver_sql(
                "ALTER TABLE integration_settings DROP COLUMN account_email"
            )
            await connection.exec_driver_sql("DROP TABLE change_request_sync_events")
            for statement in migration.REPAIR_STATEMENTS:
                await connection.exec_driver_sql(statement)
        repeat_error = None
        try:
            async with self.engine.begin() as connection:
                for statement in migration.REPAIR_STATEMENTS:
                    await connection.exec_driver_sql(statement)
        except DBAPIError as error:
            repeat_error = str(error)
        return SimpleNamespace(
            repeat_error=repeat_error,
            column=await self._fetch_value(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'integration_settings' AND column_name = 'account_email'"
            ),
            table_columns=await self._fetch_value(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'change_request_sync_events'"
            ),
            index=await self._fetch_value(
                "SELECT count(*) FROM pg_indexes "
                "WHERE indexname = 'ix_change_request_sync_events_change_request_id'"
            ),
        )

    async def _burst_forged_requests(self):
        origin = (self.parameters.REFUSAL_ADDRESS, self.parameters.REFUSAL_PORT)
        transport = httpx.ASGITransport(app=self.api, client=origin)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            answers = await asyncio.gather(
                *[
                    client.get(
                        self.parameters.REFUSAL_PATH, headers=self.parameters.REFUSAL_HEADERS
                    )
                    for _ in range(self.parameters.REFUSAL_REQUESTS)
                ]
            )
        return [answer.status_code for answer in answers]

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

    async def _seed_requirement_texts(self, prefix, rows):
        async with self.engine.begin() as connection:
            project = await self._insert_project(connection, prefix)
            for req_id, description, content_json, content_html in rows:
                await connection.execute(
                    text(
                        "INSERT INTO requirements (project_id, req_id, title, description, "
                        "content_json, content_html, status, priority, req_type, req_origin, "
                        "visibility, created_at, updated_at) VALUES (:project, :req_id, :req_id, "
                        ":description, CAST(:content_json AS JSON), :content_html, 'Draft', "
                        "'Medium', 'Functional', 'Internal', 'internal', now(), now())"
                    ),
                    {
                        "project": project,
                        "req_id": req_id,
                        "description": description,
                        "content_json": None if content_json is None else json.dumps(content_json),
                        "content_html": content_html,
                    },
                )

    async def _read_requirement_texts(self):
        async with self.engine.connect() as connection:
            rows = await connection.execute(
                text(
                    "SELECT req_id, description, content_json, content_html FROM requirements "
                    "ORDER BY req_id"
                )
            )
            return {req_id: (description, body, html) for req_id, description, body, html in rows}

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
