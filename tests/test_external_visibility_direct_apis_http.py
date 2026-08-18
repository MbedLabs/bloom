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
    CampaignSuite,
    Project,
    ProjectMembership,
    Requirement,
)
from app.models import TestCampaign as CampaignModel
from app.models import TestCampaignItem as CampaignItemModel
from app.models import TestCase as TestCaseModel
from app.models import TestSuite as TestSuiteModel
from app.models import TestSuiteItem as SuiteItemModel
from app.models import User
from app.models.user import UserRole


@dataclass
class DirectVisibilityHarness:
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
        DirectVisibilityHarness(client=client, session_maker=session_maker, actor_id=actor_id),
        engine,
    )


async def _seed_direct_visibility_data(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        external = User(
            email="external-direct@example.com",
            full_name="External User",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        session.add(external)
        await session.flush()

        project = Project(name="Direct Visibility", prefix="DVH", description="Visibility")
        session.add(project)
        await session.flush()

        session.add(
            ProjectMembership(
                user_id=external.id,
                project_id=project.id,
                role=UserRole.external.value,
            )
        )

        root_requirement = Requirement(
            project_id=project.id,
            req_id="DVH-REQ-001",
            title="Visible root requirement",
            status="Draft",
            visibility="customer",
            priority="Medium",
            req_type="Functional",
            req_origin="Customer",
        )
        session.add(root_requirement)
        await session.flush()

        visible_child_requirement = Requirement(
            project_id=project.id,
            parent_id=root_requirement.id,
            req_id="DVH-REQ-002",
            title="Visible child requirement",
            status="Draft",
            visibility="customer",
            priority="Medium",
            req_type="Functional",
            req_origin="Customer",
        )
        hidden_child_requirement = Requirement(
            project_id=project.id,
            parent_id=root_requirement.id,
            req_id="DVH-REQ-003",
            title="Hidden child requirement",
            status="Draft",
            visibility="internal",
            priority="Medium",
            req_type="Functional",
            req_origin="Internal",
        )
        hidden_requirement = Requirement(
            project_id=project.id,
            req_id="DVH-REQ-004",
            title="Hidden linked requirement",
            status="Draft",
            visibility="internal",
            priority="Medium",
            req_type="Functional",
            req_origin="Internal",
        )
        session.add_all(
            [
                visible_child_requirement,
                hidden_child_requirement,
                hidden_requirement,
            ]
        )
        await session.flush()

        visible_test_case = TestCaseModel(
            project_id=project.id,
            tc_id="DVH-TC-001",
            title="Visible test case",
            status="Approved",
            visibility="customer",
        )
        hidden_test_case = TestCaseModel(
            project_id=project.id,
            tc_id="DVH-TC-002",
            title="Hidden test case",
            status="Approved",
            visibility="internal",
        )
        session.add_all([visible_test_case, hidden_test_case])
        await session.flush()

        visible_suite = TestSuiteModel(
            project_id=project.id,
            suite_id="DVH-TS-001",
            name="Visible suite",
            status="Draft",
            visibility="customer",
        )
        hidden_suite = TestSuiteModel(
            project_id=project.id,
            suite_id="DVH-TS-002",
            name="Hidden suite",
            status="Draft",
            visibility="internal",
        )
        session.add_all([visible_suite, hidden_suite])
        await session.flush()

        visible_campaign = CampaignModel(
            project_id=project.id,
            campaign_id="DVH-CMP-001",
            name="Visible campaign",
            status="Planned",
            visibility="customer",
        )
        hidden_campaign = CampaignModel(
            project_id=project.id,
            campaign_id="DVH-CMP-002",
            name="Hidden campaign",
            status="Planned",
            visibility="internal",
        )
        session.add_all([visible_campaign, hidden_campaign])
        await session.flush()

        session.add_all(
            [
                ArtefactLink(
                    project_id=project.id,
                    source_type="TC",
                    source_id=visible_test_case.id,
                    target_type="REQ",
                    target_id=root_requirement.id,
                    role="verifies",
                ),
                ArtefactLink(
                    project_id=project.id,
                    source_type="TC",
                    source_id=visible_test_case.id,
                    target_type="REQ",
                    target_id=hidden_requirement.id,
                    role="verifies",
                ),
                ArtefactLink(
                    project_id=project.id,
                    source_type="TC",
                    source_id=hidden_test_case.id,
                    target_type="REQ",
                    target_id=root_requirement.id,
                    role="verifies",
                ),
                SuiteItemModel(suite_id=visible_suite.id, test_case_id=visible_test_case.id),
                SuiteItemModel(suite_id=hidden_suite.id, test_case_id=visible_test_case.id),
                SuiteItemModel(suite_id=hidden_suite.id, test_case_id=hidden_test_case.id),
                CampaignSuite(campaign_id=visible_campaign.id, suite_id=visible_suite.id),
                CampaignSuite(campaign_id=hidden_campaign.id, suite_id=hidden_suite.id),
                CampaignItemModel(
                    campaign_id=visible_campaign.id,
                    test_case_id=visible_test_case.id,
                    status="Pending",
                ),
                CampaignItemModel(
                    campaign_id=hidden_campaign.id,
                    test_case_id=visible_test_case.id,
                    status="Pending",
                ),
                CampaignItemModel(
                    campaign_id=hidden_campaign.id,
                    test_case_id=hidden_test_case.id,
                    status="Pending",
                ),
            ]
        )
        await session.commit()

        return {
            "external": external,
            "project": project,
            "root_requirement": root_requirement,
            "visible_child_requirement": visible_child_requirement,
            "hidden_child_requirement": hidden_child_requirement,
            "hidden_requirement": hidden_requirement,
            "visible_test_case": visible_test_case,
            "hidden_test_case": hidden_test_case,
            "visible_campaign": visible_campaign,
        }


def test_external_requirement_detail_hides_hidden_children_and_linked_objects():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_direct_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        response = harness.client.get(f"/api/requirements/{seeded['root_requirement'].id}")
        assert response.status_code == 200, response.text
        body = response.json()

        assert [child["req_id"] for child in body["children"]] == ["DVH-REQ-002"]
        assert [tc["tc_id"] for tc in body["linked_test_cases"]] == ["DVH-TC-001"]
        assert [link["test_case"]["tc_id"] for link in body["verified_by"]] == ["DVH-TC-001"]
        assert [suite["suite_id"] for suite in body["suite_backlinks"]] == ["DVH-TS-001"]
        assert [campaign["campaign_id"] for campaign in body["campaign_backlinks"]] == [
            "DVH-CMP-001"
        ]
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_external_test_case_detail_hides_hidden_requirements_and_memberships():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_direct_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        response = harness.client.get(f"/api/test-cases/{seeded['visible_test_case'].id}")
        assert response.status_code == 200, response.text
        body = response.json()

        assert [req["req_id"] for req in body["linked_requirements"]] == ["DVH-REQ-001"]
        assert [link["requirement"]["req_id"] for link in body["verifies"]] == ["DVH-REQ-001"]
        assert [suite["suite_id"] for suite in body["suite_memberships"]] == ["DVH-TS-001"]
        assert [campaign["campaign_id"] for campaign in body["campaign_memberships"]] == [
            "DVH-CMP-001"
        ]
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_external_campaign_detail_hides_hidden_nested_requirements():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_direct_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        response = harness.client.get(f"/api/campaigns/{seeded['visible_campaign'].id}")
        assert response.status_code == 200, response.text
        body = response.json()

        assert [item["test_case"]["tc_id"] for item in body["items"]] == ["DVH-TC-001"]
        assert [req["req_id"] for req in body["items"][0]["test_case"]["linked_requirements"]] == [
            "DVH-REQ-001"
        ]
        assert [req["req_id"] for req in body["related_requirements"]] == ["DVH-REQ-001"]
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
