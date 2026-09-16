import asyncio
from dataclasses import dataclass

from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import Project, ProjectMembership, ProjectVariable, User
from app.models.user import UserRole


@dataclass
class ProjectVariablesHarness:
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

    client = TestClient(app, base_url="http://test")
    harness = ProjectVariablesHarness(client=client, session_maker=session_maker, actor_id=actor_id)
    return harness, engine


async def _seed_project_variables_data(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        external = User(
            email="external@example.com",
            full_name="External User",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        maintainer = User(
            email="maintainer@example.com",
            full_name="Maintainer User",
            hashed_password=get_password_hash("unused-maintainer-password"),
            role=UserRole.maintainer,
            is_active=True,
        )
        session.add_all([external, maintainer])
        await session.flush()

        project = Project(name="Project Variables", prefix="PRV", description="Variables")
        session.add(project)
        await session.flush()

        session.add_all(
            [
                ProjectMembership(
                    user_id=external.id,
                    project_id=project.id,
                    role=UserRole.external.value,
                ),
                ProjectMembership(
                    user_id=maintainer.id,
                    project_id=project.id,
                    role=UserRole.maintainer.value,
                ),
                ProjectVariable(
                    project_id=project.id,
                    kind="parameter",
                    key="API_KEY",
                    value="super-secret-value",
                    description="Sensitive value",
                ),
            ]
        )
        await session.commit()
        await session.refresh(external)
        await session.refresh(maintainer)
        await session.refresh(project)
        return {"external": external, "maintainer": maintainer, "project": project}


def test_external_cannot_list_project_variables():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_project_variables_data(harness.session_maker))
        harness.act_as(seeded["external"])

        response = harness.client.get(
            "/api/project-variables",
            params={"project_id": seeded["project"].id},
        )
        assert response.status_code == 403, response.text
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_maintainer_can_list_project_variables():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_project_variables_data(harness.session_maker))
        harness.act_as(seeded["maintainer"])

        response = harness.client.get(
            "/api/project-variables",
            params={"project_id": seeded["project"].id},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body) == 1
        assert body[0]["key"] == "API_KEY"
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
