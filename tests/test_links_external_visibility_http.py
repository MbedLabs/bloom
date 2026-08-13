import asyncio
from dataclasses import dataclass

from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import (
    ArtefactLink,
    Project,
    ProjectMembership,
    Requirement,
    TestCase,
    User,
)
from app.models.user import UserRole


@dataclass
class LinksVisibilityHarness:
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
    harness = LinksVisibilityHarness(client=client, session_maker=session_maker, actor_id=actor_id)
    return harness, engine


async def _seed_links_visibility_data(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        external = User(
            email="external@example.com",
            full_name="External User",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        session.add(external)
        await session.flush()

        project = Project(name="Links Visibility", prefix="LKV", description="Visibility")
        session.add(project)
        await session.flush()

        session.add(
            ProjectMembership(
                user_id=external.id,
                project_id=project.id,
                role=UserRole.external.value,
            )
        )

        customer_requirement = Requirement(
            project_id=project.id,
            req_id="LKV-REQ-001",
            title="Customer requirement",
            status="Draft",
            visibility="customer",
            priority="Medium",
            req_type="Functional",
            req_origin="Customer",
        )
        internal_requirement = Requirement(
            project_id=project.id,
            req_id="LKV-REQ-002",
            title="Internal requirement",
            status="Draft",
            visibility="internal",
            priority="Medium",
            req_type="Functional",
            req_origin="Internal",
        )
        customer_test_case = TestCase(
            project_id=project.id,
            tc_id="LKV-TC-001",
            title="Customer test case",
            status="Approved",
            visibility="customer",
        )
        internal_test_case = TestCase(
            project_id=project.id,
            tc_id="LKV-TC-002",
            title="Internal test case",
            status="Approved",
            visibility="internal",
        )
        session.add_all(
            [
                customer_requirement,
                internal_requirement,
                customer_test_case,
                internal_test_case,
            ]
        )
        await session.flush()

        session.add_all(
            [
                ArtefactLink(
                    project_id=project.id,
                    source_type="TC",
                    source_id=customer_test_case.id,
                    target_type="REQ",
                    target_id=customer_requirement.id,
                    role="verifies",
                ),
                ArtefactLink(
                    project_id=project.id,
                    source_type="TC",
                    source_id=customer_test_case.id,
                    target_type="REQ",
                    target_id=internal_requirement.id,
                    role="verifies",
                ),
                ArtefactLink(
                    project_id=project.id,
                    source_type="TC",
                    source_id=internal_test_case.id,
                    target_type="REQ",
                    target_id=customer_requirement.id,
                    role="verifies",
                ),
            ]
        )
        await session.commit()
        await session.refresh(external)
        await session.refresh(project)
        return {"external": external, "project": project}


def test_external_link_list_hides_links_with_hidden_endpoints():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_links_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        response = harness.client.get(
            "/api/links",
            params={"project_id": seeded["project"].id},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body) == 1
        assert body[0]["source_type"] == "TC"
        assert body[0]["target_type"] == "REQ"
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
