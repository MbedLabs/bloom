"""Who `@` may reach, and what it discloses about them.

Mentioning a colleague is a collaboration act, not an administrative one. The
editor's `@` list used to come from the admin-only user directory, so every
maintainer got a 403 - which the editor reads as an empty list, not as an
error, so the trigger simply went quiet. These pin the rule that replaced it:
the people on the project, plus the admins who reach every project anyway.

They also pin what is *not* disclosed. Being allowed to address someone is not
being allowed to read their address, so the payload carries a name and an id
and nothing else.
"""

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
from app.models import Project, ProjectMembership, User
from app.models.user import UserRole


@dataclass
class MentionHarness:
    client: TestClient
    session_maker: async_sessionmaker[AsyncSession]
    actor_id: dict[str, int | None]

    def act_as(self, user_id: int) -> None:
        self.actor_id["value"] = user_id

    def run(self, coro):
        return asyncio.run(coro)


@pytest.fixture
def mention_harness():
    from app import models  # noqa: F401

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    actor_id: dict[str, int | None] = {"value": None}

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
                status_code=status.HTTP_401_UNAUTHORIZED, detail="No test user selected"
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
    harness = MentionHarness(client=client, session_maker=session_maker, actor_id=actor_id)

    try:
        yield harness
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def _person(email: str, name: str, role: UserRole, active: bool = True) -> User:
    return User(
        email=email,
        full_name=name,
        hashed_password=get_password_hash("unused-password"),
        role=role,
        is_active=active,
    )


async def _seed(session_maker: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    """Two maintainers on one project, and every kind of person who is not."""
    async with session_maker() as session:
        admin = _person("admin@example.com", "Ada Admin", UserRole.admin)
        grace = _person("grace@example.com", "Grace Hopper", UserRole.maintainer)
        alan = _person("alan@example.com", "Alan Turing", UserRole.maintainer)
        elsewhere = _person("else@example.com", "Elsewhere Maintainer", UserRole.maintainer)
        outsider = _person("out@example.com", "Unassigned Maintainer", UserRole.maintainer)
        retired = _person("retired@example.com", "Retired Member", UserRole.maintainer, False)
        customer = _person("customer@example.com", "Customer Contact", UserRole.external)
        session.add_all([admin, grace, alan, elsewhere, outsider, retired, customer])
        await session.flush()

        project = Project(name="Flight Controller", prefix="FLT", description="The project")
        other = Project(name="Ground Station", prefix="GND", description="A different project")
        session.add_all([project, other])
        await session.flush()

        session.add_all(
            [
                ProjectMembership(
                    user_id=grace.id, project_id=project.id, role=UserRole.maintainer.value
                ),
                ProjectMembership(
                    user_id=alan.id, project_id=project.id, role=UserRole.maintainer.value
                ),
                ProjectMembership(
                    user_id=retired.id, project_id=project.id, role=UserRole.maintainer.value
                ),
                ProjectMembership(
                    user_id=customer.id, project_id=project.id, role=UserRole.external.value
                ),
                ProjectMembership(
                    user_id=elsewhere.id, project_id=other.id, role=UserRole.maintainer.value
                ),
            ]
        )
        await session.commit()

        return {
            "admin": admin.id,
            "grace": grace.id,
            "alan": alan.id,
            "elsewhere": elsewhere.id,
            "outsider": outsider.id,
            "retired": retired.id,
            "customer": customer.id,
            "project": project.id,
            "other": other.id,
        }


def _names(payload: list[dict]) -> list[str]:
    return sorted(entry["full_name"] for entry in payload)


def test_a_maintainer_can_reach_the_other_people_on_the_project(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["grace"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    assert response.status_code == 200
    # The whole point: a maintainer sees their colleague, not a 403.
    assert "Alan Turing" in _names(response.json())


def test_the_list_is_the_project_members_plus_admins(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["grace"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    assert response.status_code == 200
    assert _names(response.json()) == [
        "Ada Admin",
        "Alan Turing",
        "Customer Contact",
        "Grace Hopper",
    ]


def test_someone_on_another_project_is_not_offered(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["grace"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    assert "Elsewhere Maintainer" not in _names(response.json())
    assert "Unassigned Maintainer" not in _names(response.json())


def test_a_deactivated_member_is_not_offered(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["grace"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    # There is no point addressing someone who cannot answer.
    assert "Retired Member" not in _names(response.json())


def test_it_discloses_a_name_and_nothing_else(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["grace"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    # Addressing a colleague must not hand out the user directory.
    for entry in response.json():
        assert set(entry) == {"id", "full_name"}


def test_a_non_member_is_refused(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["outsider"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    assert response.status_code == 403


def test_a_member_of_a_different_project_is_refused(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["elsewhere"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    assert response.status_code == 403


def test_an_admin_reaches_every_project(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["admin"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    assert response.status_code == 200
    assert "Grace Hopper" in _names(response.json())


def test_an_unknown_project_is_a_404(mention_harness):
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["admin"])

    response = mention_harness.client.get("/api/users/mentionable", params={"project_id": 999_999})

    assert response.status_code == 404


def test_mentionable_is_not_parsed_as_a_user_id(mention_harness):
    """The route sits before GET /{user_id}; if it ever moves, this fails."""
    ids = mention_harness.run(_seed(mention_harness.session_maker))
    mention_harness.act_as(ids["admin"])

    response = mention_harness.client.get(
        "/api/users/mentionable", params={"project_id": ids["project"]}
    )

    assert response.status_code != 422
