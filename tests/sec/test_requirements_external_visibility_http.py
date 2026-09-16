import asyncio
from dataclasses import dataclass

from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import Project, ProjectMembership, Requirement, User
from app.models.user import UserRole


@dataclass
class RequirementVisibilityHarness:
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
    harness = RequirementVisibilityHarness(
        client=client, session_maker=session_maker, actor_id=actor_id
    )
    return harness, engine


async def _seed_requirement_visibility_data(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        admin = User(
            email="admin@example.com",
            full_name="Admin User",
            hashed_password=get_password_hash("unused-admin-password"),
            role=UserRole.admin,
            is_active=True,
        )
        external = User(
            email="external@example.com",
            full_name="External User",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        session.add_all([admin, external])
        await session.flush()

        project = Project(name="Requirement Visibility", prefix="RQV", description="Visibility")
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
            req_id="RQV-REQ-001",
            title="Customer requirement",
            status="Draft",
            visibility="customer",
            priority="Medium",
            req_type="Functional",
            req_origin="Customer",
        )
        internal_requirement = Requirement(
            project_id=project.id,
            req_id="RQV-REQ-002",
            title="Internal requirement",
            status="Draft",
            visibility="internal",
            priority="Medium",
            req_type="Functional",
            req_origin="Internal",
        )
        session.add_all([customer_requirement, internal_requirement])
        await session.commit()

        return {
            "admin": admin,
            "external": external,
            "project": project,
            "customer_requirement": customer_requirement,
            "internal_requirement": internal_requirement,
        }


def test_external_requirement_list_hides_internal():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_requirement_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        response = harness.client.get(
            "/api/requirements",
            params={"project_id": seeded["project"].id},
        )
        assert response.status_code == 200, response.text
        req_ids = {item["req_id"] for item in response.json()["items"]}
        assert seeded["customer_requirement"].req_id in req_ids
        assert seeded["internal_requirement"].req_id not in req_ids
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_external_requirement_detail_returns_404_for_internal():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_requirement_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])

        response = harness.client.get(f"/api/requirements/{seeded['internal_requirement'].id}")
        assert response.status_code == 404, response.text
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_requirement_origin_customer_sets_customer_visibility():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_requirement_visibility_data(harness.session_maker))
        harness.act_as(seeded["admin"])

        response = harness.client.post(
            "/api/requirements",
            json={
                "project_id": seeded["project"].id,
                "title": "Customer-origin requirement",
                "req_origin": "Customer",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["req_origin"] == "Customer"
        assert body["visibility"] == "customer"
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_requirement_origin_internal_removes_customer_visibility():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_requirement_visibility_data(harness.session_maker))
        harness.act_as(seeded["admin"])

        response = harness.client.patch(
            f"/api/requirements/{seeded['customer_requirement'].id}",
            json={"req_origin": "Internal"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["req_origin"] == "Internal"
        assert body["visibility"] == "internal"
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
