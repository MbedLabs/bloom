"""Sync now and a scheduled run on one setting at once create one defect per issue."""

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import integrations
from app.core.database import Base
from app.models import Defect, IntegrationSetting, Project
from app.models.user import User, UserRole
from app.services import integration_sync
from app.services.integration_secrets import encrypt_integration_secret


async def test_sync_now_and_a_scheduled_run_create_one_defect(monkeypatch):
    """Both runs search before either writes; the setting's lock lets one create."""
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    schema = "integration_sync_" + uuid.uuid4().hex
    admin_engine = create_async_engine(url)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    searches = 0
    both_searched = asyncio.Event()

    async def jira(request):
        """Hold each creation search until both runs have sent theirs."""
        nonlocal searches
        if request.url.path.endswith("/rest/api/3/myself"):
            return httpx.Response(200, json={"accountId": "acc"})
        if request.method == "GET":
            return httpx.Response(200, json={"fields": {}})
        if "statusCategory != Done" in json.loads(request.content)["jql"]:
            searches += 1
            if searches == 2:
                both_searched.set()
            await asyncio.wait_for(both_searched.wait(), timeout=10)
            issue = {"key": "PROJ-1", "fields": {"issuetype": {"name": "Bug"}, "summary": "s"}}
            return httpx.Response(200, json={"issues": [issue], "isLast": True})
        return httpx.Response(200, json={"issues": [], "isLast": True})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(jira), **kw),
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with sessions() as db:
            admin = User(
                email="admin@example.com",
                full_name="Admin",
                hashed_password="x",
                role=UserRole.admin,
                is_active=True,
            )
            project = Project(name="Sync", prefix="SYN")
            db.add_all([admin, project])
            await db.flush()
            setting = IntegrationSetting(
                project_id=project.id,
                tracker="jira",
                base_url="https://acme.atlassian.net",
                account_email="bot@acme.test",
                token_encrypted=encrypt_integration_secret("api-token"),
                jira_project_key="PROJ",
                created_at=now - timedelta(days=1),
            )
            db.add(setting)
            await db.commit()

        async def sync_now():
            async with sessions() as db:
                await integrations.pull_jira_issues(setting.id, db=db, current_user=admin)
                await db.commit()

        await asyncio.wait_for(
            asyncio.gather(sync_now(), integration_sync.run_due(15, maker=sessions, now=now)),
            timeout=20,
        )

        async with sessions() as db:
            assert await db.scalar(select(func.count(Defect.id))) == 1
    finally:
        await engine.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()
