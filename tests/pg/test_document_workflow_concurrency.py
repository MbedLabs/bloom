"""Concurrent HTTP reads initialize one persisted document workflow."""

import asyncio
import os
import uuid

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models import ArtefactWorkflow, Project, Requirement
from app.models.user import User, UserRole


async def test_concurrent_first_reads_share_one_workflow(monkeypatch):
    """Read an existing artefact concurrently through separate real transactions."""
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    schema = "workflow_concurrency_" + uuid.uuid4().hex
    admin_engine = create_async_engine(url)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    arrived = asyncio.Event()
    count = 0
    original_execute = AsyncSession.execute

    async def synchronize_empty_lookup(session, statement, *args, **kwargs):
        """Synchronize the two initially empty workflow reads."""
        nonlocal count
        result = await original_execute(session, statement, *args, **kwargs)
        if (
            session.info.get("concurrent_reader")
            and str(statement).startswith("SELECT artefact_workflows.")
            and count < 2
        ):
            count += 1
            if count == 2:
                arrived.set()
            try:
                await asyncio.wait_for(arrived.wait(), timeout=0.25)
            except asyncio.TimeoutError:
                pass
        return result

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            user = User(
                email="reviewer@example.com",
                full_name="Reviewer",
                hashed_password="x",
                role=UserRole.admin,
                is_active=True,
            )
            project = Project(name="Demo", prefix="PRJ")
            db.add_all([user, project])
            await db.flush()
            row = Requirement(
                project_id=project.id,
                req_id="PRJ-REQ-001",
                title="Concurrent reads",
                created_by_id=user.id,
            )
            db.add(row)
            await db.commit()
            row_id = row.id

        async def session():
            async with sessions() as db:
                db.info["concurrent_reader"] = True
                try:
                    yield db
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise

        async def actor():
            return user

        app.dependency_overrides[get_db] = session
        app.dependency_overrides[get_current_user] = actor
        monkeypatch.setattr(AsyncSession, "execute", synchronize_empty_lookup)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            replies = await asyncio.wait_for(
                asyncio.gather(
                    *[client.get(f"/api/artefacts/requirement/{row_id}/workflow") for _ in range(2)]
                ),
                timeout=15,
            )
        assert [reply.status_code for reply in replies] == [200, 200], [
            reply.text for reply in replies
        ]
        async with sessions() as db:
            states = (await db.scalars(select(ArtefactWorkflow))).all()
            assert len(states) == 1
            assert states[0].revision_number == 1
            assert states[0].phase == "Draft"
            assert states[0].revision_creator_id == user.id
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            later = await client.get(f"/api/artefacts/requirement/{row_id}/workflow")
        assert later.status_code == 200, later.text
        assert later.json()["revision_number"] == replies[0].json()["revision_number"] == 1
        assert later.json()["creator"]["id"] == user.id
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        await engine.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()
