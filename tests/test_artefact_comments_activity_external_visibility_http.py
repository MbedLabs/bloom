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
    ArtefactActivity,
    ArtefactComment,
    Project,
    ProjectMembership,
    Requirement,
    User,
)
from app.models.user import UserRole


@dataclass
class ArtefactActivityHarness:
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
    harness = ArtefactActivityHarness(client=client, session_maker=session_maker, actor_id=actor_id)
    return harness, engine


async def _seed_artefact_activity_data(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as session:
        external = User(
            email="external-activity@example.com",
            full_name="External User",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        session.add(external)
        await session.flush()

        project = Project(name="Artefact Activity", prefix="AAC", description="Activity")
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
            req_id="AAC-REQ-001",
            title="Customer requirement",
            status="Draft",
            visibility="customer",
            priority="Medium",
            req_type="Functional",
            req_origin="Customer",
        )
        internal_requirement = Requirement(
            project_id=project.id,
            req_id="AAC-REQ-002",
            title="Internal requirement",
            status="Draft",
            visibility="internal",
            priority="Medium",
            req_type="Functional",
            req_origin="Internal",
        )
        session.add_all([customer_requirement, internal_requirement])
        await session.flush()

        session.add_all(
            [
                ArtefactComment(
                    artefact_type="requirement",
                    artefact_id=customer_requirement.id,
                    author_name="System",
                    body="Visible comment",
                ),
                ArtefactComment(
                    artefact_type="requirement",
                    artefact_id=internal_requirement.id,
                    author_name="System",
                    body="Hidden comment",
                ),
                ArtefactActivity(
                    artefact_type="requirement",
                    artefact_id=customer_requirement.id,
                    event_type="created",
                    summary="Visible activity",
                ),
                ArtefactActivity(
                    artefact_type="requirement",
                    artefact_id=internal_requirement.id,
                    event_type="created",
                    summary="Hidden activity",
                ),
            ]
        )
        await session.commit()

        return {
            "external": external,
            "customer_requirement": customer_requirement,
            "internal_requirement": internal_requirement,
        }


def test_external_comments_and_activity_return_404_for_internal_requirement():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_artefact_activity_data(harness.session_maker))
        harness.act_as(seeded["external"])

        hidden_comments = harness.client.get(
            f"/api/artefacts/requirement/{seeded['internal_requirement'].id}/comments"
        )
        assert hidden_comments.status_code == 404, hidden_comments.text

        hidden_activity = harness.client.get(
            f"/api/artefacts/requirement/{seeded['internal_requirement'].id}/activity"
        )
        assert hidden_activity.status_code == 404, hidden_activity.text

        visible_comments = harness.client.get(
            f"/api/artefacts/requirement/{seeded['customer_requirement'].id}/comments"
        )
        assert visible_comments.status_code == 200, visible_comments.text
        assert [comment["body"] for comment in visible_comments.json()] == ["Visible comment"]

        visible_activity = harness.client.get(
            f"/api/artefacts/requirement/{seeded['customer_requirement'].id}/activity"
        )
        assert visible_activity.status_code == 200, visible_activity.text
        assert [event["summary"] for event in visible_activity.json()] == ["Visible activity"]
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
