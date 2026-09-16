import asyncio
from dataclasses import dataclass

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import (
    Document,
    Project,
    ProjectExternalDocType,
    ProjectMembership,
    Requirement,
    User,
)
from app.models.user import UserRole


@dataclass
class VisibilityHarness:
    client: TestClient
    session_maker: async_sessionmaker[AsyncSession]
    actor_id: dict[str, int | None]

    def act_as(self, user: User) -> None:
        self.actor_id["value"] = user.id

    def run(self, coro):
        return asyncio.run(coro)


@pytest.fixture
def visibility_harness():
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
    harness = VisibilityHarness(client=client, session_maker=session_maker, actor_id=actor_id)

    try:
        yield harness
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


async def _seed_docs_visibility_data(session_maker: async_sessionmaker[AsyncSession]):
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

        project = Project(name="Visible Project", prefix="VIS", description="Visibility checks")
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
                ProjectExternalDocType(membership_id=membership.id, doc_type="REQ"),
                ProjectExternalDocType(membership_id=membership.id, doc_type="SPEC"),
            ]
        )

        customer_requirement = Requirement(
            project_id=project.id,
            req_id="VIS-REQ-001",
            title="Customer requirement",
            status="Draft",
            visibility="customer",
            priority="Medium",
            req_type="Functional",
            req_origin="Customer",
        )
        internal_requirement = Requirement(
            project_id=project.id,
            req_id="VIS-REQ-002",
            title="Internal requirement",
            status="Draft",
            visibility="internal",
            priority="Medium",
            req_type="Functional",
            req_origin="Internal",
        )
        customer_spec = Document(
            project_id=project.id,
            doc_id="VIS-SPEC-001",
            title="Customer specification",
            doc_type="SPEC",
            visibility="customer",
            status="Draft",
            version="1.0",
        )
        internal_spec = Document(
            project_id=project.id,
            doc_id="VIS-SPEC-002",
            title="Internal specification",
            doc_type="SPEC",
            visibility="internal",
            status="Draft",
            version="1.0",
        )
        session.add_all([customer_requirement, internal_requirement, customer_spec, internal_spec])
        await session.commit()

        return {
            "admin": admin,
            "external": external,
            "project": project,
            "customer_requirement": customer_requirement,
            "internal_requirement": internal_requirement,
            "customer_spec": customer_spec,
            "internal_spec": internal_spec,
        }


def test_external_docs_facade_list_only_returns_customer_visible_items(
    visibility_harness: VisibilityHarness,
):
    seeded = visibility_harness.run(_seed_docs_visibility_data(visibility_harness.session_maker))
    visibility_harness.act_as(seeded["external"])

    response = visibility_harness.client.get(
        f"/api/projects/{seeded['project'].prefix}/docs",
        params=[("type", "REQ"), ("type", "SPEC")],
    )
    assert response.status_code == 200, response.text

    rows = response.json()["items"]
    doc_ids = {row["doc_id"] for row in rows}
    visibilities = {row["doc_id"]: row["visibility"] for row in rows}

    assert seeded["customer_requirement"].req_id in doc_ids
    assert seeded["customer_spec"].doc_id in doc_ids
    assert seeded["internal_requirement"].req_id not in doc_ids
    assert seeded["internal_spec"].doc_id not in doc_ids
    assert visibilities[seeded["customer_requirement"].req_id] == "customer"
    assert visibilities[seeded["customer_spec"].doc_id] == "customer"


@pytest.mark.parametrize(
    ("kind_slug", "obj_key", "field_name", "expected_status"),
    [
        ("requirements", "customer_requirement", "req_id", 200),
        ("requirements", "internal_requirement", "req_id", 404),
        ("specifications", "customer_spec", "doc_id", 200),
        ("specifications", "internal_spec", "doc_id", 404),
    ],
)
def test_external_docs_facade_detail_hides_internal_items(
    visibility_harness: VisibilityHarness,
    kind_slug: str,
    obj_key: str,
    field_name: str,
    expected_status: int,
):
    seeded = visibility_harness.run(_seed_docs_visibility_data(visibility_harness.session_maker))
    visibility_harness.act_as(seeded["external"])

    doc_id = getattr(seeded[obj_key], field_name)
    response = visibility_harness.client.get(
        f"/api/projects/{seeded['project'].prefix}/docs/{kind_slug}/{doc_id}"
    )
    assert response.status_code == expected_status, response.text
