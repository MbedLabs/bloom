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
from app.models import (
    CampaignSuite,
    Project,
    ProjectMembership,
    Requirement,
    TestCampaign,
    TestCampaignItem,
    TestCase,
    TestSuite,
    User,
)
from app.models.user import UserRole


@dataclass
class CampaignVisibilityHarness:
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
        CampaignVisibilityHarness(client=client, session_maker=session_maker, actor_id=actor_id),
        engine,
    )


async def _seed_campaign_visibility_data(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        external = User(
            email="external-campaign@example.com",
            full_name="External User",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        session.add(external)
        await session.flush()

        project = Project(name="Campaign Visibility", prefix="CPV", description="Visibility")
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
            tc_id="CPV-TC-001",
            title="Visible test case",
            status="Draft",
            visibility="customer",
        )
        hidden_tc = TestCase(
            project_id=project.id,
            tc_id="CPV-TC-002",
            title="Hidden test case",
            status="Draft",
            visibility="internal",
        )
        visible_req = Requirement(
            project_id=project.id,
            req_id="CPV-REQ-001",
            title="Visible requirement",
            status="Draft",
            visibility="customer",
            priority="Medium",
            req_type="Functional",
            req_origin="Customer",
        )
        hidden_req = Requirement(
            project_id=project.id,
            req_id="CPV-REQ-002",
            title="Hidden requirement",
            status="Draft",
            visibility="internal",
            priority="Medium",
            req_type="Functional",
            req_origin="Internal",
        )
        visible_suite = TestSuite(
            project_id=project.id,
            suite_id="CPV-TS-001",
            name="Visible suite",
            status="Draft",
            visibility="customer",
        )
        hidden_suite = TestSuite(
            project_id=project.id,
            suite_id="CPV-TS-002",
            name="Hidden suite",
            status="Draft",
            visibility="internal",
        )
        session.add_all(
            [visible_tc, hidden_tc, visible_req, hidden_req, visible_suite, hidden_suite]
        )
        await session.flush()

        visible_campaign = TestCampaign(
            project_id=project.id,
            campaign_id="CPV-CMP-001",
            name="Visible campaign",
            status="Planned",
            visibility="customer",
        )
        hidden_campaign = TestCampaign(
            project_id=project.id,
            campaign_id="CPV-CMP-002",
            name="Hidden campaign",
            status="Planned",
            visibility="internal",
        )
        session.add_all([visible_campaign, hidden_campaign])
        await session.flush()

        session.add_all(
            [
                CampaignSuite(campaign_id=visible_campaign.id, suite_id=visible_suite.id),
                CampaignSuite(campaign_id=visible_campaign.id, suite_id=hidden_suite.id),
                TestCampaignItem(
                    campaign_id=visible_campaign.id,
                    test_case_id=visible_tc.id,
                    status="Executed",
                    result="Passed",
                    executed_at=datetime(2026, 7, 2, 11, 15, 0),
                ),
                TestCampaignItem(
                    campaign_id=visible_campaign.id, test_case_id=hidden_tc.id, status="Pending"
                ),
                TestCampaignItem(
                    campaign_id=hidden_campaign.id, test_case_id=visible_tc.id, status="Pending"
                ),
            ]
        )
        await session.commit()

        return {
            "external": external,
            "project": project,
            "visible_campaign": visible_campaign,
            "hidden_campaign": hidden_campaign,
        }


def test_external_campaign_list_and_detail_hide_internal_campaign_and_items():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_campaign_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        listed = harness.client.get(f"/api/campaigns?project_id={seeded['project'].id}")
        assert listed.status_code == 200, listed.text
        campaign_ids = {item["campaign_id"] for item in listed.json()["items"]}
        assert campaign_ids == {"CPV-CMP-001"}

        hidden = harness.client.get(f"/api/campaigns/{seeded['hidden_campaign'].id}")
        assert hidden.status_code == 404, hidden.text

        visible = harness.client.get(f"/api/campaigns/{seeded['visible_campaign'].id}")
        assert visible.status_code == 200, visible.text
        body = visible.json()
        assert body["visibility"] == "customer"
        assert body["total_items"] == 1
        assert body["last_execution_status"] == "Passed"
        assert body["last_executed_at"].startswith("2026-07-02T11:15:00")
        assert [item["test_case"]["tc_id"] for item in body["items"]] == ["CPV-TC-001"]
        assert [suite["suite"]["suite_id"] for suite in body["suite_scopes"]] == ["CPV-TS-001"]
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_campaign_list_includes_latest_execution_timestamp():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_campaign_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        listed = harness.client.get(f"/api/campaigns?project_id={seeded['project'].id}")

        assert listed.status_code == 200, listed.text
        items = listed.json()["items"]
        assert len(items) == 1
        assert items[0]["campaign_id"] == "CPV-CMP-001"
        assert items[0]["total_items"] == 1
        assert items[0]["last_execution_status"] == "Passed"
        assert items[0]["last_executed_at"].startswith("2026-07-02T11:15:00")
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


async def _seed_campaign_sync_maintainer(
    session_maker: async_sessionmaker[AsyncSession],
    project_id: int,
):
    async with session_maker() as session:
        maintainer = User(
            email="campaign-sync-maintainer@example.com",
            full_name="Campaign Sync Maintainer",
            hashed_password=get_password_hash("unused-maintainer-password"),
            role=UserRole.maintainer,
            is_active=True,
        )
        session.add(maintainer)
        await session.flush()

        session.add(
            ProjectMembership(
                user_id=maintainer.id,
                project_id=project_id,
                role=UserRole.maintainer.value,
            )
        )
        await session.commit()
        return maintainer


def test_sync_results_updates_items_without_inventing_campaign_run_id():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_campaign_visibility_data(harness.session_maker))
        maintainer = harness.run(
            _seed_campaign_sync_maintainer(
                harness.session_maker,
                seeded["project"].id,
            )
        )
        harness.act_as(maintainer)

        response = harness.client.post(
            "/api/campaigns/sync-results",
            json={
                "results": [
                    {
                        "tc_id": "CPV-TC-001",
                        "status": "Passed",
                        "comment": "Last result from Bud run 123",
                        "executed_at": "2026-07-04T10:45:00",
                        "bud_run_id": 123,
                    }
                ]
            },
        )

        assert response.status_code == 200, response.text
        visible = harness.client.get(f"/api/campaigns/{seeded['visible_campaign'].id}")
        assert visible.status_code == 200, visible.text
        body = visible.json()
        assert body["bud_run_id"] is None
        assert body["bud_run_url"] is None
        assert body["items"][0]["result"] == "Passed"
        assert body["items"][0]["executed_at"].startswith("2026-07-04T10:45:00")
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
