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
    Project,
    ProjectMembership,
    Requirement,
    TestCase,
    TestSuite,
    TestSuiteItem,
    User,
)
from app.models.user import UserRole


@dataclass
class SuiteVisibilityHarness:
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
    return (
        SuiteVisibilityHarness(client=client, session_maker=session_maker, actor_id=actor_id),
        engine,
    )


async def _seed_suite_visibility_data(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        external = User(
            email="external-suite@example.com",
            full_name="External User",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        session.add(external)
        await session.flush()

        project = Project(name="Suite Visibility", prefix="TSV", description="Visibility")
        session.add(project)
        await session.flush()

        session.add(
            ProjectMembership(
                user_id=external.id,
                project_id=project.id,
                role=UserRole.external.value,
            )
        )

        visible_tc = TestCase(
            project_id=project.id,
            tc_id="TSV-TC-001",
            title="Visible test case",
            status="Draft",
            visibility="customer",
        )
        hidden_tc = TestCase(
            project_id=project.id,
            tc_id="TSV-TC-002",
            title="Hidden test case",
            status="Draft",
            visibility="internal",
        )
        visible_req = Requirement(
            project_id=project.id,
            req_id="TSV-REQ-001",
            title="Visible requirement",
            status="Draft",
            visibility="customer",
            priority="Medium",
            req_type="Functional",
            req_origin="Customer",
        )
        session.add_all([visible_tc, hidden_tc, visible_req])
        await session.flush()

        visible_suite = TestSuite(
            project_id=project.id,
            suite_id="TSV-TS-001",
            name="Visible suite",
            status="Draft",
            visibility="customer",
        )
        hidden_suite = TestSuite(
            project_id=project.id,
            suite_id="TSV-TS-002",
            name="Hidden suite",
            status="Draft",
            visibility="internal",
        )
        session.add_all([visible_suite, hidden_suite])
        await session.flush()

        session.add_all(
            [
                TestSuiteItem(suite_id=visible_suite.id, test_case_id=visible_tc.id, order=0),
                TestSuiteItem(suite_id=visible_suite.id, test_case_id=hidden_tc.id, order=1),
                TestSuiteItem(suite_id=hidden_suite.id, test_case_id=visible_tc.id, order=0),
            ]
        )
        await session.commit()

        return {
            "external": external,
            "project": project,
            "visible_suite": visible_suite,
            "hidden_suite": hidden_suite,
        }


def test_external_suite_list_and_detail_hide_internal_suite_and_items():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_suite_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        listed = harness.client.get(f"/api/test-suites?project_id={seeded['project'].id}")
        assert listed.status_code == 200, listed.text
        suite_ids = {item["suite_id"] for item in listed.json()["items"]}
        assert suite_ids == {"TSV-TS-001"}

        hidden = harness.client.get(f"/api/test-suites/{seeded['hidden_suite'].id}")
        assert hidden.status_code == 404, hidden.text

        visible = harness.client.get(f"/api/test-suites/{seeded['visible_suite'].id}")
        assert visible.status_code == 200, visible.text
        body = visible.json()
        assert body["visibility"] == "customer"
        assert [item["test_case"]["tc_id"] for item in body["items"]] == ["TSV-TC-001"]
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
