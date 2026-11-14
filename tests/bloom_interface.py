"""
* @file     ${tests/bloom_interface.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Interface every Bloom test layer shares: test database, records and fake trackers.
* @author   Amine El Omari
* @date     2026-11-09
* @version  1.0.0
* @note     Calls run on the interface's own loop, on in-memory SQLite unless a layer swaps the database.
"""

import asyncio
import contextlib
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import tests.parameters as params
from app.api import integrations
from app.core.database import Base
from app.models import (
    ChangeRequest,
    ChangeRequestSyncEvent,
    Defect,
    DefectSyncEvent,
    IntegrationSetting,
    Project,
)
from app.models.user import User, UserRole
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
        self._release_database()
        self.loop.close()

    def _release_database(self):
        pass

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

    def bloom_jira_key(self, number, project=None):
        return f"{project or self.parameters.JIRA_PROJECT}-{number}"

    def bloom_serve(self, answer):
        def handler(request):
            self.site.calls.append(request.url)
            return answer(request)

        def client(**kw):
            return REAL_CLIENT(transport=httpx.MockTransport(handler), **kw)

        self.patches.enter_context(patch.object(httpx, "AsyncClient", client))

    def bloom_refuse_with(self, status, headers=None, body=None):
        self.bloom_serve(
            lambda request: httpx.Response(status, headers=headers or {}, json=body or {})
        )

    def bloom_make_unreachable(self):
        def answer(request):
            raise httpx.ConnectError(self.parameters.JIRA_UNREACHABLE, request=request)

        self.bloom_serve(answer)

    def bloom_maintainer_role(self):
        return UserRole.maintainer

    def bloom_add_user(self, email, role):
        return self._run(
            self._add(User(email=email, full_name=email, hashed_password=email, role=role))
        )

    def bloom_list_defects(self):
        return self._run(self._all(select(Defect).order_by(Defect.id)))

    def bloom_sync_now(self, setting_id, admin_email):
        async def pull(db, admin):
            return await integrations.pull_jira_issues(setting_id, db=db, current_user=admin)

        return self._run(self._as_admin(admin_email, pull))

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

    async def _serve_session(self):
        async with self.maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

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

    async def _as_admin(self, email, call):
        async with self.maker() as db:
            admin = User(email=email, full_name=email, hashed_password=email, role=UserRole.admin)
            db.add(admin)
            await db.flush()
            result = await call(db, admin)
            await db.commit()
            return result
