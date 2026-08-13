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
    ChangeRequest,
    Defect,
    DesignItem,
    Project,
    ProjectMembership,
    RiskItem,
    TestConcept,
    User,
)
from app.models.user import UserRole


@dataclass
class ArtefactVisibilityHarness:
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
        ArtefactVisibilityHarness(client=client, session_maker=session_maker, actor_id=actor_id),
        engine,
    )


async def _seed_controlled_artefact_visibility_data(
    session_maker: async_sessionmaker[AsyncSession],
):
    async with session_maker() as session:
        external = User(
            email="external-controlled@example.com",
            full_name="External User",
            hashed_password=get_password_hash("unused-external-password"),
            role=UserRole.external,
            is_active=True,
        )
        session.add(external)
        await session.flush()

        project = Project(name="Controlled Visibility", prefix="CTV", description="Visibility")
        session.add(project)
        await session.flush()

        session.add(
            ProjectMembership(
                user_id=external.id,
                project_id=project.id,
                role=UserRole.external.value,
            )
        )
        await session.flush()

        visible_design = DesignItem(
            project_id=project.id,
            design_id="CTV-DES-001",
            title="Visible design",
            status="Draft",
            priority="Medium",
            design_type="Architecture",
            visibility="customer",
        )
        hidden_design = DesignItem(
            project_id=project.id,
            design_id="CTV-DES-002",
            title="Hidden design",
            status="Draft",
            priority="Medium",
            design_type="Architecture",
            visibility="internal",
        )

        visible_risk = RiskItem(
            project_id=project.id,
            risk_id="CTV-RSK-001",
            title="Visible risk",
            status="Open",
            severity="Medium",
            probability="Medium",
            risk_category="Technical",
            visibility="customer",
        )
        hidden_risk = RiskItem(
            project_id=project.id,
            risk_id="CTV-RSK-002",
            title="Hidden risk",
            status="Open",
            severity="Medium",
            probability="Medium",
            risk_category="Technical",
            visibility="internal",
        )

        visible_change = ChangeRequest(
            project_id=project.id,
            change_id="CTV-CHG-001",
            title="Visible change",
            status="Submitted",
            priority="Medium",
            change_type="Enhancement",
            visibility="customer",
        )
        hidden_change = ChangeRequest(
            project_id=project.id,
            change_id="CTV-CHG-002",
            title="Hidden change",
            status="Submitted",
            priority="Medium",
            change_type="Enhancement",
            visibility="internal",
        )

        visible_concept = TestConcept(
            project_id=project.id,
            concept_id="CTV-CPT-001",
            name="Visible concept",
            status="Draft",
            coverage=0,
            visibility="customer",
        )
        hidden_concept = TestConcept(
            project_id=project.id,
            concept_id="CTV-CPT-002",
            name="Hidden concept",
            status="Draft",
            coverage=0,
            visibility="internal",
        )

        visible_defect = Defect(
            project_id=project.id,
            defect_id="CTV-DEF-001",
            title="Visible defect",
            status="Open",
            severity="Medium",
            priority="Medium",
            visibility="customer",
        )
        hidden_defect = Defect(
            project_id=project.id,
            defect_id="CTV-DEF-002",
            title="Hidden defect",
            status="Open",
            severity="Medium",
            priority="Medium",
            visibility="internal",
        )

        session.add_all(
            [
                visible_design,
                hidden_design,
                visible_risk,
                hidden_risk,
                visible_change,
                hidden_change,
                visible_concept,
                hidden_concept,
                visible_defect,
                hidden_defect,
            ]
        )
        await session.commit()

        return {
            "external": external,
            "project": project,
            "design": (visible_design, hidden_design),
            "risk": (visible_risk, hidden_risk),
            "change": (visible_change, hidden_change),
            "concept": (visible_concept, hidden_concept),
            "defect": (visible_defect, hidden_defect),
        }


def test_external_controlled_artefacts_hide_internal_rows_and_return_visibility():
    harness, engine = _build_harness()
    try:
        seeded = harness.run(_seed_controlled_artefact_visibility_data(harness.session_maker))
        harness.act_as(seeded["external"])
        project_id = seeded["project"].id

        cases = [
            ("design", "/api/designs", "design_id", "CTV-DES-001", seeded["design"]),
            ("risk", "/api/risks", "risk_id", "CTV-RSK-001", seeded["risk"]),
            ("change", "/api/changes", "change_id", "CTV-CHG-001", seeded["change"]),
            ("concept", "/api/test-concepts", "concept_id", "CTV-CPT-001", seeded["concept"]),
            ("defect", "/api/defects", "defect_id", "CTV-DEF-001", seeded["defect"]),
        ]

        for _label, base_path, public_id_field, expected_visible_public_id, pair in cases:
            visible_item, hidden_item = pair

            listed = harness.client.get(f"{base_path}?project_id={project_id}")
            assert listed.status_code == 200, listed.text
            listed_ids = {row[public_id_field] for row in listed.json()["items"]}
            assert listed_ids == {expected_visible_public_id}

            hidden = harness.client.get(f"{base_path}/{hidden_item.id}")
            assert hidden.status_code == 404, hidden.text

            visible = harness.client.get(f"{base_path}/{visible_item.id}")
            assert visible.status_code == 200, visible.text
            assert visible.json()["visibility"] == "customer"
            assert visible.json()[public_id_field] == expected_visible_public_id
    finally:
        harness.client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
