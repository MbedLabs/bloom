import asyncio
from dataclasses import dataclass

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.cache import dashboard_stats_cache
from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import Project, ProjectMembership, Requirement, User
from app.models.user import UserRole


@dataclass
class IamHttpHarness:
    client: TestClient
    session_maker: async_sessionmaker[AsyncSession]
    actor_id: dict[str, int | None]

    def act_as(self, user: User) -> None:
        self.actor_id["value"] = user.id

    def run(self, coro):
        return asyncio.run(coro)


@pytest.fixture
def iam_http_harness():
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
    harness = IamHttpHarness(client=client, session_maker=session_maker, actor_id=actor_id)

    try:
        yield harness
    finally:
        client.close()
        app.dependency_overrides.clear()
        dashboard_stats_cache._store.clear()
        asyncio.run(engine.dispose())


async def _seed_iam_fixture_data(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        admin = User(
            email="admin@example.com",
            full_name="Admin User",
            hashed_password=get_password_hash("unused-admin-password"),
            role=UserRole.admin,
            is_active=True,
        )
        maintainer = User(
            email="maintainer@example.com",
            full_name="Scoped Maintainer",
            hashed_password=get_password_hash("unused-maintainer-password"),
            role=UserRole.maintainer,
            is_active=True,
        )
        external = User(
            email="external@example.com",
            full_name="Read Only External",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        session.add_all([admin, maintainer, external])
        await session.flush()

        allowed = Project(name="Allowed Project", prefix="ALW", description="Visible")
        blocked = Project(name="Blocked Project", prefix="BLK", description="Hidden")
        session.add_all([allowed, blocked])
        await session.flush()

        session.add_all(
            [
                ProjectMembership(
                    user_id=maintainer.id,
                    project_id=allowed.id,
                    role=UserRole.maintainer.value,
                ),
                ProjectMembership(
                    user_id=external.id,
                    project_id=allowed.id,
                    role=UserRole.external.value,
                ),
            ]
        )

        blocked_requirement = Requirement(
            project_id=blocked.id,
            req_id="BLK-REQ-001",
            title="Blocked requirement",
            description="Should not leak across projects",
            status="Draft",
            priority="Medium",
            req_type="Functional",
            req_origin="System",
        )
        session.add(blocked_requirement)
        await session.commit()
        await session.refresh(admin)
        await session.refresh(maintainer)
        await session.refresh(external)
        await session.refresh(allowed)
        await session.refresh(blocked)
        await session.refresh(blocked_requirement)

        return {
            "admin": admin,
            "maintainer": maintainer,
            "external": external,
            "allowed": allowed,
            "blocked": blocked,
            "blocked_requirement": blocked_requirement,
        }


def test_unassigned_maintainer_cannot_access_other_project_data(iam_http_harness: IamHttpHarness):
    seeded = iam_http_harness.run(_seed_iam_fixture_data(iam_http_harness.session_maker))
    iam_http_harness.act_as(seeded["maintainer"])

    projects = iam_http_harness.client.get("/api/projects")
    assert projects.status_code == 200
    project_ids = {project["id"] for project in projects.json()}
    assert project_ids == {seeded["allowed"].id}

    blocked_list = iam_http_harness.client.get(
        "/api/requirements",
        params={"project_id": seeded["blocked"].id},
    )
    assert blocked_list.status_code == 403

    blocked_get = iam_http_harness.client.get(
        f"/api/requirements/{seeded['blocked_requirement'].id}"
    )
    assert blocked_get.status_code == 403

    blocked_traceability = iam_http_harness.client.get(
        "/api/traceability",
        params={"project_id": seeded["blocked"].id},
    )
    assert blocked_traceability.status_code == 403

    dashboard = iam_http_harness.client.get("/api/dashboard/stats")
    assert dashboard.status_code == 200
    dashboard_project_ids = {project["id"] for project in dashboard.json()["projects"]}
    assert seeded["blocked"].id not in dashboard_project_ids
    assert dashboard_project_ids == {seeded["allowed"].id}

    blocked_import = iam_http_harness.client.post(
        f"/api/projects/{seeded['allowed'].id}/import",
        json={
            "source_project_id": seeded["blocked"].id,
            "doc_type": "REQ",
            "doc_ids": [seeded["blocked_requirement"].id],
            "include_links": True,
        },
    )
    assert blocked_import.status_code == 403


def test_external_viewer_cannot_upload_reqif(iam_http_harness: IamHttpHarness):
    seeded = iam_http_harness.run(_seed_iam_fixture_data(iam_http_harness.session_maker))
    iam_http_harness.act_as(seeded["external"])

    response = iam_http_harness.client.post(
        f"/api/projects/{seeded['allowed'].id}/import/reqif",
        files={"file": ("requirements.reqif", b"<REQ-IF/>", "application/xml")},
    )

    assert response.status_code == 403
