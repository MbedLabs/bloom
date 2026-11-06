"""
* @file     ${tests/bloom_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface of Bloom's tests: test database, records, fake trackers and app calls.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Every call runs on the interface's own event loop against an in-memory database.
"""

import asyncio
import contextlib
import hashlib
import hmac
import json
import os
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import tests.parameters as params
from app import main
from app.api import integrations
from app.core.database import Base, get_db
from app.models import (
    ChangeRequest,
    ChangeRequestSyncEvent,
    Defect,
    DefectSyncEvent,
    IntegrationSetting,
    Project,
)
from app.models import TestCase as TestCaseModel
from app.models.user import User, UserRole
from app.services import integration_sync
from app.services.integration_secrets import encrypt_integration_secret

REAL_CLIENT = httpx.AsyncClient


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

    def bloom_use_postgres(self):
        url = os.environ.get(self.parameters.DATABASE_SETTING, "")
        if not url.startswith(self.parameters.POSTGRES_SCHEME):
            return False
        parts = urlsplit(url)
        self.pg_admin_url = urlunsplit(parts._replace(path=f"/{self.parameters.PG_ADMIN_DATABASE}"))
        self.pg_database = f"{self.parameters.PG_DATABASE_PREFIX}{uuid.uuid4().hex[:12]}"
        self._run(self.engine.dispose())
        self._run(self._create_postgres_database())
        self.engine = create_async_engine(urlunsplit(parts._replace(path=f"/{self.pg_database}")))
        self._run(self._create_tables())
        self.maker = async_sessionmaker(self.engine, expire_on_commit=False)
        return True

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
