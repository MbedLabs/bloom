"""HTTP tests for dashboard stats (TST-005)."""

import asyncio
import os
from dataclasses import dataclass

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.cache import dashboard_stats_cache
from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import (
    Project,
    ProjectExternalDocType,
    ProjectMembership,
    Requirement,
    TestCampaign,
    TestCase,
    User,
)
from app.models.user import UserRole


def test_dashboard_stats_shape(api_client: TestClient):
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = api_client.get("/api/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "total_projects",
        "total_requirements",
        "total_test_cases",
        "coverage_percent",
        "projects",
    ):
        assert key in data
    assert isinstance(data["projects"], list)

    # Cached second call should match
    resp2 = api_client.get("/api/dashboard/stats", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["total_projects"] == data["total_projects"]


@dataclass
class DashboardVisibilityHarness:
    client: TestClient
    session_maker: async_sessionmaker[AsyncSession]
    actor_id: dict[str, int | None]

    def act_as(self, user: User) -> None:
        self.actor_id["value"] = user.id

    def run(self, coro):
        return asyncio.run(coro)


def _build_dashboard_harness():
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
    dashboard_stats_cache._store.clear()

    client = TestClient(app, base_url="http://test")
    harness = DashboardVisibilityHarness(
        client=client, session_maker=session_maker, actor_id=actor_id
    )
    return harness, engine


async def _seed_dashboard_visibility_data(
    session_maker: async_sessionmaker[AsyncSession],
    allowed_doc_types: tuple[str, ...] = ("REQ", "TC", "CMP"),
):
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

        project = Project(name="Dashboard Visibility", prefix="DSV", description="Visibility")
        session.add(project)
        await session.flush()

        membership = ProjectMembership(
            user_id=external.id,
            project_id=project.id,
            role=UserRole.external.value,
        )
        session.add(membership)
        await session.flush()
        session.add_all(
            [
                ProjectExternalDocType(membership_id=membership.id, doc_type=doc_type)
                for doc_type in allowed_doc_types
            ]
        )

        session.add_all(
            [
                Requirement(
                    project_id=project.id,
                    req_id="DSV-REQ-001",
                    title="Customer requirement",
                    status="Draft",
                    visibility="customer",
                    priority="Medium",
                    req_type="Functional",
                    req_origin="Customer",
                ),
                Requirement(
                    project_id=project.id,
                    req_id="DSV-REQ-002",
                    title="Internal requirement",
                    status="Draft",
                    visibility="internal",
                    priority="Medium",
                    req_type="Functional",
                    req_origin="Internal",
                ),
                TestCase(
                    project_id=project.id,
                    tc_id="DSV-TC-001",
                    title="Customer test case",
                    status="Draft",
                    visibility="customer",
                ),
                TestCase(
                    project_id=project.id,
                    tc_id="DSV-TC-002",
                    title="Internal test case",
                    status="Draft",
                    visibility="internal",
                ),
                TestCampaign(
                    project_id=project.id,
                    campaign_id="DSV-CMP-001",
                    name="Customer campaign",
                    status="Planned",
                    visibility="customer",
                ),
                TestCampaign(
                    project_id=project.id,
                    campaign_id="DSV-CMP-002",
                    name="Internal campaign",
                    status="Planned",
                    visibility="internal",
                ),
            ]
        )
        await session.commit()
        await session.refresh(external)
        await session.refresh(project)

        return {"external": external, "project": project}


def test_external_dashboard_ignores_internal_artefacts():
    harness, engine = _build_dashboard_harness()
    try:
        seeded = harness.run(_seed_dashboard_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        response = harness.client.get("/api/dashboard/stats")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total_requirements"] == 1
        assert body["total_test_cases"] == 1
        assert body["total_campaigns"] == 1
        assert body["uncovered_requirements"] == 1
        assert body["projects"][0]["uncovered_requirement_count"] == 1

        projects_response = harness.client.get("/api/projects")
        assert projects_response.status_code == 200, projects_response.text
        project_summary = projects_response.json()[0]
        assert project_summary["requirement_count"] == 1
        assert project_summary["test_case_count"] == 1
        assert project_summary["campaign_count"] == 1
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        dashboard_stats_cache._store.clear()
        asyncio.run(engine.dispose())


def test_external_dashboard_honors_document_type_allowlist():
    harness, engine = _build_dashboard_harness()
    try:
        seeded = harness.run(
            _seed_dashboard_visibility_data(harness.session_maker, allowed_doc_types=("CMP",))
        )
        harness.act_as(seeded["external"])

        response = harness.client.get("/api/dashboard/stats")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total_requirements"] == 0
        assert body["total_test_cases"] == 0
        assert body["total_campaigns"] == 1
        assert body["uncovered_requirements"] == 0
        assert body["projects"][0]["requirement_count"] == 0
        assert body["projects"][0]["test_case_count"] == 0

        projects_response = harness.client.get("/api/projects")
        assert projects_response.status_code == 200, projects_response.text
        project_summary = projects_response.json()[0]
        assert project_summary["requirement_count"] == 0
        assert project_summary["test_case_count"] == 0
        assert project_summary["campaign_count"] == 1
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        dashboard_stats_cache._store.clear()
        asyncio.run(engine.dispose())
