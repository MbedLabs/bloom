import asyncio
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import Project, ProjectMembership, TestCase, User
from app.models.user import UserRole


@dataclass
class DocsHarness:
    client: TestClient
    session_maker: async_sessionmaker[AsyncSession]
    actor_id: dict[str, int | None]

    def act_as(self, user: User) -> None:
        self.actor_id["value"] = user.id

    def run(self, coro):
        return asyncio.run(coro)


def _build_harness():
    from app import models  # noqa: F401

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    actor_id = {"value": None}

    async def _create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_get_current_user() -> User:
        user_id = actor_id["value"]
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No test user selected",
            )
        async with session_maker() as session:
            user = await session.get(User, user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Selected test user no longer exists",
                )
            return user

    asyncio.run(_create_schema())
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    return DocsHarness(TestClient(app, base_url="http://test"), session_maker, actor_id), engine


async def _seed_tc_doc(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        maintainer = User(
            email="maintainer-docs@example.com",
            full_name="Maintainer Docs",
            hashed_password=get_password_hash("unused-password"),
            role=UserRole.maintainer,
            is_active=True,
        )
        session.add(maintainer)
        await session.flush()

        project = Project(name="Docs Bud Links", prefix="DBL", description="Bud links")
        session.add(project)
        await session.flush()

        session.add(
            ProjectMembership(
                user_id=maintainer.id,
                project_id=project.id,
                role=UserRole.maintainer.value,
            )
        )

        tc = TestCase(
            project_id=project.id,
            tc_id="DBL-TC-001",
            title="Clickable Bud run",
            status="Draft",
            visibility="customer",
            last_execution_status="Passed",
            last_executed_at=datetime(2026, 7, 4, 9, 30, 0),
            last_bud_run_id=987,
        )
        session.add(tc)
        await session.commit()
        return maintainer, project


def test_docs_facade_exposes_last_bud_run_id_for_tc_rows():
    harness, engine = _build_harness()
    try:
        maintainer, project = harness.run(_seed_tc_doc(harness.session_maker))
        harness.act_as(maintainer)

        response = harness.client.get(f"/api/projects/{project.prefix}/docs?type=TC")

        assert response.status_code == 200, response.text
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["doc_id"] == "DBL-TC-001"
        assert items[0]["last_bud_run_id"] == 987
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
