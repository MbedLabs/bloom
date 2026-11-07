"""
* @file     ${tests/bloom_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface of Bloom's tests: test database, records, fake trackers and app calls.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Calls run on the interface's own loop, on in-memory SQLite or a new PostgreSQL database.
"""

import asyncio
import base64
import contextlib
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from sqlalchemy import bindparam, event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import tests.parameters as params
from app import main
from app.api import access_requests as access_requests_api
from app.api import cli_auth as cli_auth_api
from app.api import docs_facade, integrations
from app.core import id_generator
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.deps import limiter
from app.core.permissions import DOC_TYPE_RESOURCES
from app.core.security import create_access_token, get_current_user, get_password_hash
from app.models import (
    ChangeRequest,
    ChangeRequestSyncEvent,
    Defect,
    DefectSyncEvent,
    Document,
    IntegrationSetting,
    Project,
)
from app.models import TestCase as TestCaseModel
from app.models.cli_auth_session import CliAuthSession
from app.models.user import User, UserRole
from app.schemas import ProjectCreate
from app.services import cli_auth, integration_sync
from app.services.integration_secrets import encrypt_integration_secret
from app.services.token_service import hash_token, invalidate_all_refresh_tokens
from tests.access_fixtures import (
    allow_doc_types,
    project_access_fixture,
    scenario_rules,
)

REAL_CLIENT = httpx.AsyncClient
ROOT = Path(__file__).resolve().parents[1]


class BloomInterface:

    def setUp(self):
        self.parameters = params
        self.loop = asyncio.new_event_loop()
        self.patches = contextlib.ExitStack()
        self.engine = create_async_engine(self.parameters.SYNC_DATABASE)
        self._run(self._create_tables())
        self.maker = async_sessionmaker(self.engine, expire_on_commit=False)
        self.site = SimpleNamespace(jql=[], reads=[], calls=[])

    def tearDown(self):
        self.patches.close()
        self._run(self.engine.dispose())
        if getattr(self, "pg_database", None):
            self._run(self._drop_postgres_database())
            self.pg_database = None
        self.loop.close()

    def bloom_create_project(self, prefix=None):
        prefix = prefix or self.parameters.SYNC_PROJECT_PREFIX
        return self._run(self._add(Project(name=f"Project {prefix}", prefix=prefix)))

    def bloom_create_integration(self, project_id, tracker="jira", **fields):
        created = self.parameters.NOW - self.parameters.SETTING_AGE
        values = {
            "project_id": project_id,
            "tracker": tracker,
            "token_encrypted": encrypt_integration_secret(self.parameters.SYNC_TOKEN),
            "enabled": True,
            "created_at": created,
            "updated_at": created,
        }
        if tracker == "jira":
            values.update(
                base_url=self.parameters.JIRA_URL,
                account_email=self.parameters.JIRA_ACCOUNT,
                jira_project_key=self.parameters.JIRA_PROJECT,
            )
        values.update(fields)
        return self._run(self._add(IntegrationSetting(**values)))

    def bloom_link_defect(self, project_id, tracker, repo, number, **fields):
        return self._run(self._link_defect(project_id, tracker, repo, number, fields))

    def bloom_link_change(self, project_id, tracker, repo, number, status):
        return self._run(self._link_change(project_id, tracker, repo, number, status))

    def bloom_get_setting(self, setting_id):
        return self._run(self._get(IntegrationSetting, setting_id))

    def bloom_get_defect(self, defect_id):
        return self._run(self._get(Defect, defect_id))

    def bloom_get_change(self, change_id):
        return self._run(self._get(ChangeRequest, change_id))

    def bloom_count_defects(self):
        return self._run(self._scalar(select(func.count(Defect.id))))

    def bloom_list_defects_linked_to(self, number):
        return self._run(self._all(select(Defect).where(Defect.external_issue_number == number)))

    def bloom_list_defect_events(self):
        return self._run(self._all(select(DefectSyncEvent).order_by(DefectSyncEvent.id)))

    def bloom_list_change_events(self):
        return self._run(
            self._all(select(ChangeRequestSyncEvent).order_by(ChangeRequestSyncEvent.id))
        )

    def bloom_get_setting_response(self, setting_id):
        setting = self.bloom_get_setting(setting_id)
        return json.loads(integrations._setting_response(setting).model_dump_json())

    def bloom_build_jira_issue(self, key, kind=None, category=None, status=None, **fields):
        return {
            "key": key,
            "fields": {
                "issuetype": {"name": kind or self.parameters.BUG},
                "status": {
                    "name": status or self.parameters.JIRA_TO_DO,
                    "statusCategory": {"key": category or self.parameters.JIRA_NEW},
                },
                "summary": fields.pop("summary", key),
                **fields,
            },
        }

    def bloom_jira_key(self, number, project=None):
        return f"{project or self.parameters.JIRA_PROJECT}-{number}"

    def bloom_jira_time(self, moment, offset_hours):
        local = moment + timedelta(hours=offset_hours)
        sign = "+" if offset_hours >= 0 else "-"
        return f"{local:%Y-%m-%dT%H:%M:%S}.000{sign}{abs(offset_hours):02d}00"

    def bloom_git_time(self, moment):
        return f"{moment:%Y-%m-%dT%H:%M:%S}Z"

    def bloom_serve_jira(self, creation=(), changed=(), issue_status=None):
        statuses = issue_status or {}

        def answer(request):
            path = request.url.path
            if path.endswith(self.parameters.JIRA_MYSELF):
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"accountId": self.parameters.JIRA_ACCOUNT}
                )
            if request.method == "POST" and path.endswith(self.parameters.JIRA_SEARCH):
                query = json.loads(request.content)["jql"]
                self.site.jql.append(query)
                issues = creation if self.parameters.CREATION_MARK in query else changed
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"issues": list(issues), "isLast": True}
                )
            if request.method == "GET" and self.parameters.JIRA_ISSUE in path:
                key = path.rsplit("/", 1)[1]
                self.site.reads.append(key)
                return httpx.Response(
                    statuses.get(key, self.parameters.STATUS_OK), json={"fields": {}}
                )
            return httpx.Response(self.parameters.STATUS_SERVER_ERROR)

        self.bloom_serve(answer)

    def bloom_serve(self, answer):
        def handler(request):
            self.site.calls.append(request.url)
            return answer(request)

        def client(**kw):
            return REAL_CLIENT(transport=httpx.MockTransport(handler), **kw)

        self.patches.enter_context(patch.object(httpx, "AsyncClient", client))

    def bloom_serve_issue_list(self, issues, unreadable_repo=None, unreadable_status=None):
        def answer(request):
            if unreadable_repo and request.url.path.startswith(f"/repos/{unreadable_repo}"):
                return httpx.Response(unreadable_status, json=[])
            return httpx.Response(self.parameters.STATUS_OK, json=list(issues))

        self.bloom_serve(answer)

    def bloom_serve_redirect(self, repo, status, location, issues):
        def answer(request):
            if request.url.path.startswith(f"/repos/{repo}"):
                return httpx.Response(status, headers={"location": location})
            return httpx.Response(self.parameters.STATUS_OK, json=list(issues))

        self.bloom_serve(answer)

    def bloom_serve_by_repo(self, answers):
        def answer(request):
            for repo, (status, headers, body) in answers.items():
                if request.url.path.startswith(f"/repos/{repo}/"):
                    return httpx.Response(status, headers=headers, json=body)
            return httpx.Response(self.parameters.STATUS_NOT_FOUND, json={})

        self.bloom_serve(answer)

    def bloom_refuse_with(self, status, headers=None, body=None):
        self.bloom_serve(
            lambda request: httpx.Response(status, headers=headers or {}, json=body or {})
        )

    def bloom_make_unreachable(self):
        def answer(request):
            raise httpx.ConnectError(self.parameters.JIRA_UNREACHABLE, request=request)

        self.bloom_serve(answer)

    def bloom_cap_searches(self, cap):
        self.patches.enter_context(patch.object(integrations, "MAX_PULLED_ISSUES", cap))
        self.patches.enter_context(patch.object(integration_sync, "MAX_PULLED_ISSUES", cap))

    def bloom_check_removals(self, count):
        self.patches.enter_context(patch.object(integration_sync, "REMOVAL_CHECKS", count))

    def bloom_save_during_search(self, setting_id, label, when):
        async def save(setting):
            async with self.maker() as db:
                row = await db.get(IntegrationSetting, setting_id)
                row.jira_label = label
                row.updated_at = when
                await db.commit()

        self._after_each_search(save)

    def bloom_link_defect_during_search(self, project_id, number):
        async def link(setting):
            await self._link_defect(project_id, "jira", self.parameters.JIRA_PROJECT, number, {})

        self._after_each_search(link)

    def bloom_fail_search_of(self, project_key, text):
        original = integration_sync._fetch_jira

        async def fetch(setting, **kw):
            if setting.jira_project_key == project_key:
                raise RuntimeError(text)
            return await original(setting, **kw)

        self.patches.enter_context(patch.object(integration_sync, "_fetch_jira", fetch))

    def bloom_run_sync(self, now):
        return self._run(integration_sync.run_due(maker=self.maker, now=now))

    def bloom_claim(self, setting_id, minutes, now):
        return self._run(integration_sync.claim(self.maker, setting_id, minutes, now))

    def bloom_save_setting(self, setting_id, admin_email, **changes):
        async def save(db, admin):
            update = integrations.IntegrationSettingUpdate(**changes)
            return await integrations.update_integration_setting(
                setting_id, update, db=db, current_user=admin
            )

        self._run(self._as_admin(admin_email, save))

    def bloom_start_api(self):
        app = FastAPI()
        app.include_router(integrations.router, prefix=self.parameters.INTEGRATIONS_PREFIX)

        async def database():
            async with self.maker() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = database
        self.api = app

    def bloom_create_webhook_integration(self, project_id, **fields):
        return self.bloom_create_integration(
            project_id,
            webhook_secret=encrypt_integration_secret(self.parameters.WEBHOOK_SECRET),
            **fields,
        )

    def bloom_create_webhook_environment(self, change_status=None, **setting_fields):
        project_id = self.bloom_create_project()
        fields = {"jira_project_key": None, **setting_fields}
        setting_id = self.bloom_create_webhook_integration(project_id, **fields)
        defect_id = self.bloom_link_defect(
            project_id, "jira", self.parameters.JIRA_PROJECT, self.parameters.LINKED_NUMBER
        )
        change_id = self.bloom_link_change(
            project_id,
            "jira",
            self.parameters.JIRA_PROJECT,
            self.parameters.CHANGE_NUMBER,
            change_status or self.parameters.CHANGE_SUBMITTED,
        )
        self.bloom_start_api()
        return SimpleNamespace(
            project_id=project_id, setting_id=setting_id, defect_id=defect_id, change_id=change_id
        )

    def bloom_jira_webhook_body(self, issue_key, event=None, **fields):
        issue_fields = {
            "summary": self.parameters.WEBHOOK_SUMMARY,
            "issuetype": {"name": self.parameters.BUG},
            "status": {
                "name": self.parameters.JIRA_DONE,
                "statusCategory": {"key": self.parameters.JIRA_DONE_CATEGORY},
            },
        }
        issue_fields.update(fields)
        payload = {
            "webhookEvent": event or self.parameters.ISSUE_UPDATED,
            "issue": {"key": issue_key, "fields": issue_fields},
        }
        return json.dumps(payload).encode()

    def bloom_jira_event_body(self, event):
        return json.dumps({"webhookEvent": event}).encode()

    def bloom_sign(self, body):
        digest = hmac.new(self.parameters.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return f"{self.parameters.SIGNATURE_PREFIX}{digest}"

    def bloom_post_jira_webhook(self, body, signature=None, delivery=None, signed=True):
        headers = {"Content-Type": "application/json"}
        if signed:
            headers["X-Hub-Signature"] = (
                signature if signature is not None else self.bloom_sign(body)
            )
        if delivery is not None:
            headers["X-Atlassian-Webhook-Identifier"] = delivery
        return self._run(self._post(self.parameters.WEBHOOK_PATH, body, headers))

    def bloom_set_defect_status(self, defect_id, status):
        self._run(self._update(Defect, defect_id, status=status))

    def bloom_update_setting(self, setting_id, **fields):
        self._run(self._update(IntegrationSetting, setting_id, **fields))

    def bloom_add_test_case(self, project_id, tc_id, title):
        return self._run(self._add(TestCaseModel(project_id=project_id, tc_id=tc_id, title=title)))

    def bloom_maintainer_role(self):
        return UserRole.maintainer

    def bloom_add_user(self, email, role):
        return self._run(
            self._add(User(email=email, full_name=email, hashed_password=email, role=role))
        )

    def bloom_list_defects(self):
        return self._run(self._all(select(Defect).order_by(Defect.id)))

    def bloom_log_sync_event(self, target, target_id, event_type):
        async def log():
            async with self.maker() as db:
                integrations._log_target_sync_event(
                    db, target, target_id, "inbound", "jira", event_type
                )
                await db.commit()

        self._run(log())

    def bloom_record_pushes(self):
        pushed = []

        async def push(target, setting, changed):
            pushed.append(target.id)

        self.patches.enter_context(patch.object(integrations, "_push_to_jira", push))
        return pushed

    def bloom_push_edits(self, defect_id, change_id, changes):
        async def edit():
            async with self.maker() as db:
                defect = await db.get(Defect, defect_id)
                change = await db.get(ChangeRequest, change_id)
                await integrations.sync_defect_to_tracker(db, defect, changes)
                await integrations.sync_change_request_to_tracker(db, change, changes)

        self._run(edit())

    def bloom_serve_jira_pages(self, pages):
        seen = []

        def answer(request):
            if request.url.path.endswith(self.parameters.JIRA_MYSELF):
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"accountId": self.parameters.JIRA_ACCOUNT}
                )
            if request.method == "GET":
                return httpx.Response(self.parameters.STATUS_OK, json={"fields": {}})
            seen.append(json.loads(request.content))
            if len(seen) > len(pages):
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"issues": [], "isLast": True}
                )
            return httpx.Response(self.parameters.STATUS_OK, json=pages[len(seen) - 1])

        self.bloom_serve(answer)
        return seen

    def bloom_serve_atlassian_gateway(self, cloud_id, issues):
        gateway = f"{self.parameters.ATLASSIAN_GATEWAY}/{cloud_id}/"

        def answer(request):
            url = str(request.url)
            if url.endswith(self.parameters.TENANT_INFO):
                return httpx.Response(self.parameters.STATUS_OK, json={"cloudId": cloud_id})
            if url.startswith(gateway):
                if request.url.path.endswith(self.parameters.JIRA_MYSELF):
                    return httpx.Response(
                        self.parameters.STATUS_OK, json={"accountId": self.parameters.JIRA_ACCOUNT}
                    )
                return httpx.Response(
                    self.parameters.STATUS_OK, json={"issues": list(issues), "isLast": True}
                )
            return httpx.Response(self.parameters.STATUS_UNAUTHORIZED)

        self.bloom_serve(answer)

    def bloom_try_sync_now(self, setting_id, admin_email):
        try:
            return self.bloom_sync_now(setting_id, admin_email), None
        except HTTPException as exc:
            return None, (exc.status_code, exc.detail)

    def bloom_try_validate_jira_filter(self, issue_types, priority_map):
        try:
            integrations._validate_jira_filter(issue_types, priority_map)
        except HTTPException as exc:
            return exc.status_code, exc.detail
        return None

    def bloom_link_defect_before_reserving(self, project_id, number, title):
        original = integrations._reserve_webhook_delivery

        async def reserve(db, setting, tracker, delivery_id):
            await self._link_defect(
                project_id, "jira", self.parameters.JIRA_PROJECT, number, {"title": title}
            )
            return await original(db, setting, tracker, delivery_id)

        self.patches.enter_context(patch.object(integrations, "_reserve_webhook_delivery", reserve))

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

    def bloom_compute_next_id(self, existing_ids, prefix, type_code):
        try:
            return id_generator.compute_next_id(existing_ids, prefix, type_code), None
        except ValueError as exc:
            return None, type(exc).__name__

    def bloom_list_docs_routes(self):
        return [route.path for route in docs_facade.router.routes]

    def bloom_forge_token(self, user_id, algorithm, minutes):
        user = self._run(self._get(User, user_id))
        expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        claims = {
            "sub": str(user.id),
            "type": "user",
            "ver": user.session_version,
            "exp": int(expires.timestamp()),
        }
        signing_input = f"{self._token_part({'alg': algorithm, 'typ': 'JWT'})}."
        signing_input += self._token_part(claims)
        hashes = {"HS256": hashlib.sha256, "HS512": hashlib.sha512}
        if algorithm not in hashes:
            return f"{signing_input}."
        digest = hmac.new(
            settings.SECRET_KEY.encode(), signing_input.encode(), hashes[algorithm]
        ).digest()
        return f"{signing_input}.{base64.urlsafe_b64encode(digest).rstrip(b'=').decode()}"

    def bloom_issue_token(self, user_id):
        user = self._run(self._get(User, user_id))
        return create_access_token(
            {"sub": str(user.id), "type": "user", "ver": user.session_version}
        )

    def bloom_sign_in_with_token(self, token):
        return self._run(self._sign_in_with_token(token))

    def bloom_run_smoke_script_with_fake_docker(self, image):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "docker-argv.jsonl"
            docker = Path(folder) / "docker"
            docker.write_text(self._fake_docker(), encoding="utf-8")
            docker.chmod(0o755)
            env = {**os.environ, "DOCKER_ARGV_LOG": str(log)}
            env["PATH"] = f"{folder}{os.pathsep}{env['PATH']}"
            subprocess.run(
                ["bash", str(ROOT / self.parameters.SMOKE_SCRIPT), image],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            if not log.exists():
                return []
            return [json.loads(line) for line in log.read_text().splitlines()]

    def bloom_read_smoke_project_payload(self):
        script = (ROOT / self.parameters.SMOKE_SCRIPT).read_text(encoding="utf-8")
        match = re.search(self.parameters.SMOKE_PAYLOAD_PATTERN, script)
        return json.loads(match.group(1)) if match else None

    def bloom_validate_project_payload(self, payload):
        try:
            return ProjectCreate.model_validate(payload).prefix, None
        except ValidationError as exc:
            return None, str(exc)

    def bloom_start_full_api(self):
        self.patches.enter_context(patch.dict(main.app.dependency_overrides))
        main.app.dependency_overrides[get_db] = self._serve_session
        self.patches.enter_context(patch.object(limiter, "enabled", False))
        self.api = main.app

    def bloom_add_admin(self, email, password):
        return self.bloom_add_account(email, password, UserRole.admin.value)

    def bloom_add_account(self, email, password, role):
        return self._run(
            self._add(
                User(
                    email=email,
                    full_name=email,
                    hashed_password=get_password_hash(password),
                    role=UserRole(role),
                    is_active=True,
                )
            )
        )

    def bloom_add_external_member(self, project_id, user_id, permissions, visibility):
        self._run(self._add_external_member(project_id, user_id, permissions, visibility))

    def bloom_add_document(self, project_id, doc_id, title, visibility):
        return self._run(
            self._add(
                Document(
                    project_id=project_id,
                    doc_id=doc_id,
                    title=title,
                    doc_type=self.parameters.DOCUMENT_TYPE,
                    visibility=visibility,
                    status=self.parameters.DOCUMENT_STATUS,
                    version=self.parameters.DOCUMENT_VERSION,
                )
            )
        )

    def bloom_api_list_documents(self, headers, project_id):
        return self._run(self._request("GET", f"/api/projects/{project_id}/documents", headers))

    def bloom_api_get_document(self, headers, document_id):
        return self._run(self._request("GET", f"/api/documents/{document_id}", headers))

    def bloom_api_me(self, headers):
        answer = self._run(self._request("GET", "/api/auth/me", headers))
        return answer.json().get("id") if answer.status_code == 200 else None

    def bloom_api_create_artefact(self, headers, kind, project_id, title, **fields):
        body = {"project_id": project_id, "title": title, **fields}
        if kind == self.parameters.DOCUMENT_KIND:
            body.setdefault("doc_type", self.parameters.DOCUMENT_TYPE)
            path = f"/api/projects/{project_id}/documents"
        else:
            path = self.parameters.ARTEFACT_PATHS[kind]
        return self._run(self._request("POST", path, headers, json=body))

    def bloom_api_update_artefact(self, headers, kind, artefact_id, body):
        path = f"{self.parameters.ARTEFACT_PATHS[kind]}/{artefact_id}"
        return self._run(self._request("PATCH", path, headers, json=body))

    def bloom_api_activity_types(self, headers, kind, artefact_id):
        path = f"/api/artefacts/{kind}/{artefact_id}/activity"
        answer = self._run(self._request("GET", path, headers))
        if answer.status_code != 200:
            return None
        return [event["event_type"] for event in answer.json()]

    def bloom_api_sign_off(self, headers, kind, artefact_id, step):
        path = f"/api/artefacts/{kind}/{artefact_id}/sign-off"
        return self._run(self._request("POST", path, headers, json={"step": step}))

    def bloom_api_review(self, headers, kind, artefact_id, reviewer_id):
        base = f"/api/artefacts/{kind}/{artefact_id}"
        assigned = self._run(
            self._request(
                "PUT",
                base + "/workflow/assignees",
                headers,
                json={"reviewer_id": reviewer_id, "approver_id": reviewer_id},
            )
        )
        requested = self._run(
            self._request(
                "POST", base + "/requests", headers, json={"kind": self.parameters.REVIEW_REQUEST}
            )
        )
        commented = self._run(
            self._request(
                "POST", base + "/comments", headers, json={"body": self.parameters.REVIEW_COMMENT}
            )
        )
        signed = self.bloom_api_sign_off(headers, kind, artefact_id, self.parameters.REVIEW_STEP)
        return [assigned.status_code, requested.status_code, commented.status_code], signed

    def bloom_api_link(self, headers, project_id, source_id, target_id):
        body = {
            "project_id": project_id,
            "source_type": self.parameters.LINK_SOURCE,
            "source_id": source_id,
            "target_type": self.parameters.LINK_TARGET,
            "target_id": target_id,
            "role": self.parameters.LINK_ROLE,
        }
        return self._run(self._request("POST", "/api/links", headers, json=body))

    def bloom_api_list_docs(self, headers, prefix, doc_type):
        path = f"/api/projects/{prefix}/docs"
        return self._run(self._request("GET", path, headers, params={"type": doc_type}))

    def bloom_log_in(self, email, password):
        answer = self._run(
            self._request("POST", "/api/auth/login", json={"email": email, "password": password})
        )
        token = answer.json().get("access_token") if answer.status_code == 200 else None
        return {"Authorization": f"Bearer {token}"}, answer.status_code

    def bloom_api_create_project(self, headers, prefix):
        body = {"name": f"Project {prefix}", "prefix": prefix}
        return self._run(self._request("POST", "/api/projects", headers, json=body))

    def bloom_api_create_baseline(self, headers, project_id, name):
        body = {"project_id": project_id, "name": name}
        return self._run(self._request("POST", "/api/baselines", headers, json=body))

    def bloom_api_create_user(self, headers, email, password, role, full_name=None):
        body = {
            "email": email,
            "full_name": full_name or email,
            "password": password,
            "role": role,
        }
        return self._run(self._request("POST", "/api/users", headers, json=body))

    def bloom_api_create_policy(self, headers, name, permissions, types=None):
        return self.bloom_api_create_policy_rules(
            headers, name, scenario_rules(permissions, "internal", types)
        )

    def bloom_api_create_policy_rules(self, headers, name, rules):
        body = {"name": name, "rules": rules}
        return self._run(self._request("POST", "/api/policies", headers, json=body))

    def bloom_api_create_group(self, headers, name, policy_ids):
        body = {"name": name, "description": name, "policy_ids": policy_ids}
        return self._run(self._request("POST", "/api/groups", headers, json=body))

    def bloom_api_add_group_member(self, headers, group_id, user_id):
        path = f"/api/groups/{group_id}/members"
        return self._run(self._request("POST", path, headers, json={"user_id": user_id}))

    def bloom_api_admit_group(self, headers, group_id, project_id):
        path = f"/api/groups/{group_id}/grants"
        return self._run(self._request("POST", path, headers, json={"project_id": project_id}))

    def bloom_api_add_project_member(self, headers, project_id, user_id, policy_ids, owner=False):
        path = f"/api/projects/{project_id}/members"
        body = {"user_id": user_id, "policy_ids": policy_ids}
        if owner:
            body["owner"] = True
        return self._run(self._request("POST", path, headers, json=body))

    def bloom_api_update_project_member(self, headers, project_id, member_id, policy_ids):
        path = f"/api/projects/{project_id}/members/{member_id}"
        body = {"policy_ids": policy_ids}
        return self._run(self._request("PATCH", path, headers, json=body))

    def bloom_api_get_group(self, headers, group_id):
        return self._run(self._request("GET", f"/api/groups/{group_id}", headers))

    def bloom_api_read_baselines(self, headers, project_id, baseline_id):
        listed = self._run(
            self._request("GET", "/api/baselines", headers, params={"project_id": project_id})
        )
        detail = self._run(self._request("GET", f"/api/baselines/{baseline_id}", headers))
        return listed, detail

    def bloom_capture_access_request_mail(self):
        sent = []
        self.patches.enter_context(
            patch.object(
                access_requests_api,
                "send_access_request_email",
                lambda **mail: sent.append(mail),
            )
        )
        return sent

    def bloom_api_create_requirement(self, headers, project_id, title, status):
        body = {"project_id": project_id, "title": title, "status": status}
        return self._run(self._request("POST", "/api/requirements", headers, json=body))

    def bloom_api_open_requirement_doc(self, headers, prefix, ref):
        path = f"/api/projects/{prefix}/docs/requirements/{ref}"
        return self._run(self._request("GET", path, headers))

    def bloom_api_request_access(self, headers, resource_type, resource_ref, prefix):
        body = {
            "resource_type": resource_type,
            "resource_ref": str(resource_ref),
            "project_prefix": prefix,
        }
        return self._run(self._request("POST", "/api/access-requests", headers, json=body))

    def bloom_api_my_access_request(self, headers, resource_type, resource_ref, prefix):
        query = {
            "resource_type": resource_type,
            "resource_ref": str(resource_ref),
            "project_prefix": prefix,
        }
        return self._run(self._request("GET", "/api/access-requests/mine", headers, params=query))

    def bloom_api_list_access_requests(self, headers, prefix):
        query = {"project_prefix": prefix}
        return self._run(self._request("GET", "/api/access-requests", headers, params=query))

    def bloom_api_get_requirement(self, headers, requirement_id):
        return self._run(self._request("GET", f"/api/requirements/{requirement_id}", headers))

    def bloom_api_get_user(self, headers, user_id):
        return self._run(self._request("GET", f"/api/users/{user_id}", headers))

    def bloom_api_audit_event(self, headers, action, target_type, target_id):
        query = {"action": action, "target_type": target_type, "target_id": str(target_id)}
        page = self._run(self._request("GET", "/api/audit", headers, params=query))
        items = page.json().get("items") if page.status_code == 200 else None
        return items[0] if items else None

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

    def bloom_sync_now(self, setting_id, admin_email):
        async def pull(db, admin):
            return await integrations.pull_jira_issues(setting_id, db=db, current_user=admin)

        return self._run(self._as_admin(admin_email, pull))

    def bloom_count_lifespan_starts(self, minutes):
        started = []

        async def loop():
            started.append(True)
            await asyncio.Event().wait()

        async def reconcile(session):
            return SimpleNamespace(leader_acquired=False)

        async def cycle():
            async with main.lifespan(main.app):
                await asyncio.sleep(0)

        with (
            patch.object(main.settings, "INTEGRATION_SYNC_MINUTES", minutes),
            patch.object(main.settings, "RUN_STARTUP_DATA_REPAIR", False),
            patch.object(main.settings, "AUTO_SEED_ADMIN", False),
            patch.object(main.integration_sync, "sync_loop", loop),
            patch.object(main, "reconcile_attachments", reconcile),
        ):
            self._run(cycle())
        return len(started)

    def _run(self, coroutine):
        return self.loop.run_until_complete(coroutine)

    async def _create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _add(self, row):
        async with self.maker() as db:
            db.add(row)
            await db.commit()
            return row.id

    async def _get(self, model, row_id):
        async with self.maker() as db:
            return await db.get(model, row_id)

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

    async def _update(self, model, row_id, **fields):
        async with self.maker() as db:
            row = await db.get(model, row_id)
            for name, value in fields.items():
                setattr(row, name, value)
            await db.commit()

    async def _post(self, path, body, headers):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.post(path, content=body, headers=headers)

    async def _serve_session(self):
        async with self.maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

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

    async def _add_external_member(self, project_id, user_id, permissions, visibility):
        async with self.maker() as db:
            membership = project_access_fixture(
                user_id=user_id,
                project_id=project_id,
                permissions=permissions,
                visibility=visibility,
                doc_types=[],
            )
            db.add(membership)
            await db.flush()
            for doc_type in DOC_TYPE_RESOURCES:
                allow_doc_types(membership.policies[0], [doc_type])
            await db.commit()

    async def _request(self, method, path, headers=None, json=None, params=None):
        transport = httpx.ASGITransport(app=self.api)
        async with REAL_CLIENT(transport=transport, base_url=self.parameters.API_BASE) as client:
            return await client.request(method, path, headers=headers, json=json, params=params)

    def _fake_docker(self):
        return (
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['DOCKER_ARGV_LOG'], 'a', encoding='utf-8') as log:\n"
            "    log.write(json.dumps(args) + '\\n')\n"
            "if 'current' in args:\n"
            f"    print('{self.parameters.SMOKE_ALEMBIC_HEAD} (head)')\n"
            "    sys.exit(0)\n"
            "if args and args[0] == 'run' and '--name' in args:\n"
            "    name = args[args.index('--name') + 1]\n"
            f"    if name.startswith('{self.parameters.SMOKE_APP_CONTAINER}'):\n"
            f"        sys.exit({self.parameters.SMOKE_STOP_CODE})\n"
        )

    def _token_part(self, value):
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    async def _sign_in_with_token(self, token):
        async with self.maker() as db:
            try:
                return (await get_current_user(token=token, db=db)).id, None
            except HTTPException as exc:
                return None, exc.status_code

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

    async def _scalar(self, query):
        async with self.maker() as db:
            return await db.scalar(query)

    async def _all(self, query):
        async with self.maker() as db:
            return list((await db.scalars(query)).all())

    async def _link_defect(self, project_id, tracker, repo, number, fields):
        async with self.maker() as db:
            count = await db.scalar(select(func.count(Defect.id)))
        defect = Defect(
            project_id=project_id,
            defect_id=f"{self.parameters.SYNC_PROJECT_PREFIX}-DEF-{count + 101:03d}",
            title=fields.pop("title", self.parameters.OLD_TITLE),
            status=fields.pop("status", self.parameters.DEFECT_OPEN),
            external_tracker=tracker,
            external_repo_full_name=repo,
            external_issue_number=number,
            **fields,
        )
        return await self._add(defect)

    async def _link_change(self, project_id, tracker, repo, number, status):
        async with self.maker() as db:
            count = await db.scalar(select(func.count(ChangeRequest.id)))
        change = ChangeRequest(
            project_id=project_id,
            change_id=f"{self.parameters.SYNC_PROJECT_PREFIX}-CR-{count + 101:03d}",
            title=self.parameters.OLD_TITLE,
            status=status,
            external_tracker=tracker,
            external_repo_full_name=repo,
            external_issue_number=number,
        )
        return await self._add(change)

    def _after_each_search(self, action):
        original = integration_sync._fetch_jira

        async def fetch(setting, **kw):
            fetched = await original(setting, **kw)
            await action(setting)
            return fetched

        self.patches.enter_context(patch.object(integration_sync, "_fetch_jira", fetch))

    async def _as_admin(self, email, call):
        async with self.maker() as db:
            admin = User(email=email, full_name=email, hashed_password=email, role=UserRole.admin)
            db.add(admin)
            await db.flush()
            result = await call(db, admin)
            await db.commit()
            return result
