"""Tests for the additive group/policy entitlement layer:

the group-aware require_project_access / user_can_access_project /
get_external_doc_types in app/core/security.py, plus the default-policy specs.
A user in no group must resolve exactly to their direct membership, so nothing
regresses; a group grant only ever adds access.
"""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.policy_seed import DEFAULT_POLICIES
from app.core.security import (
    _group_project_role,
    get_external_doc_types,
    require_project_access,
    user_can_access_project,
)
from app.models import Project, ProjectMembership, User, UserRole
from app.models.groups import Group, GroupMembership, GroupProjectGrant, Policy
from app.schemas.memberships import EXTERNAL_DOC_TYPES

_seq = iter(range(1, 100000))


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db
    await engine.dispose()


async def _user(db, role=UserRole.external):
    u = User(email=f"u{next(_seq)}@test.local", full_name="U", hashed_password="x", role=role)
    db.add(u)
    await db.flush()
    return u


async def _project(db):
    n = next(_seq)
    p = Project(name=f"P{n}", prefix="PRJ")
    db.add(p)
    await db.flush()
    return p


async def _grant_group(
    db, user, base_role, *, project=None, all_projects=False, doc_tag_scope=None
):
    pol = Policy(
        name=f"pol{next(_seq)}",
        base_role=base_role,
        permissions={},
        doc_tag_scope=doc_tag_scope,
    )
    db.add(pol)
    await db.flush()
    g = Group(name=f"grp{next(_seq)}", policy_id=pol.id)
    db.add(g)
    await db.flush()
    db.add(GroupProjectGrant(group_id=g.id, project_id=None if all_projects else project.id))
    db.add(GroupMembership(group_id=g.id, user_id=user.id))
    await db.flush()
    return g


@pytest.mark.asyncio
async def test_direct_membership_role_unchanged(session):
    user = await _user(session, UserRole.maintainer)
    proj = await _project(session)
    session.add(ProjectMembership(user_id=user.id, project_id=proj.id, role="maintainer"))
    await session.flush()
    assert await user_can_access_project(session, user, proj.id, roles={"maintainer"}) is True
    assert await _group_project_role(session, user.id, proj.id) is None


@pytest.mark.asyncio
async def test_group_grant_applies(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    await _grant_group(session, user, "maintainer", project=proj)
    assert await _group_project_role(session, user.id, proj.id) == "maintainer"
    assert await user_can_access_project(session, user, proj.id, roles={"maintainer"}) is True
    membership = await require_project_access(session, user, proj.id, roles={"maintainer"})
    assert membership is None


@pytest.mark.asyncio
async def test_strongest_wins(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    session.add(ProjectMembership(user_id=user.id, project_id=proj.id, role="external"))
    await session.flush()
    await _grant_group(session, user, "maintainer", project=proj)
    assert await user_can_access_project(session, user, proj.id, roles={"maintainer"}) is True


@pytest.mark.asyncio
async def test_all_projects_grant_covers_project(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    await _grant_group(session, user, "maintainer", all_projects=True)
    assert await _group_project_role(session, user.id, proj.id) == "maintainer"


@pytest.mark.asyncio
async def test_no_grant_no_access(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    assert await _group_project_role(session, user.id, proj.id) is None
    assert await user_can_access_project(session, user, proj.id) is False
    with pytest.raises(HTTPException):
        await require_project_access(session, user, proj.id)


@pytest.mark.asyncio
async def test_admin_accesses_every_project(session):
    user = await _user(session, UserRole.admin)
    proj = await _project(session)
    assert await user_can_access_project(session, user, proj.id) is True


@pytest.mark.asyncio
async def test_removing_from_group_removes_access(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    await _grant_group(session, user, "maintainer", project=proj)
    assert await _group_project_role(session, user.id, proj.id) == "maintainer"
    membership = (
        await session.execute(select(GroupMembership).where(GroupMembership.user_id == user.id))
    ).scalar_one()
    await session.delete(membership)
    await session.flush()
    assert await _group_project_role(session, user.id, proj.id) is None


def test_default_policies_are_well_formed():
    names = [spec["name"] for spec in DEFAULT_POLICIES]
    assert len(names) == len(set(names)) == 9
    assert {"Administrator", "External Reader"} <= set(names)
    for spec in DEFAULT_POLICIES:
        assert spec["base_role"] in {"admin", "maintainer", "external"}
        scope = spec.get("doc_tag_scope")
        assert scope is None or set(scope) <= EXTERNAL_DOC_TYPES


@pytest.mark.asyncio
async def test_group_external_doc_scope_enforced(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    await _grant_group(session, user, "external", project=proj, doc_tag_scope=["REQ", "TC"])
    assert await get_external_doc_types(session, user, proj.id) == {"REQ", "TC"}


@pytest.mark.asyncio
async def test_group_external_doc_scope_none_means_all(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    await _grant_group(session, user, "external", project=proj, doc_tag_scope=None)
    assert await get_external_doc_types(session, user, proj.id) is None


@pytest.mark.asyncio
async def test_group_external_doc_scope_unions_across_groups(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    await _grant_group(session, user, "external", project=proj, doc_tag_scope=["REQ"])
    await _grant_group(session, user, "external", project=proj, doc_tag_scope=["DEF"])
    assert await get_external_doc_types(session, user, proj.id) == {"REQ", "DEF"}


@pytest.mark.asyncio
async def test_group_maintainer_sees_every_doc_type(session):
    user = await _user(session, UserRole.maintainer)
    proj = await _project(session)
    await _grant_group(session, user, "maintainer", project=proj, doc_tag_scope=["REQ"])
    assert await get_external_doc_types(session, user, proj.id) is None


@pytest.mark.asyncio
async def test_no_group_external_still_forbidden(session):
    user = await _user(session, UserRole.external)
    proj = await _project(session)
    with pytest.raises(HTTPException):
        await get_external_doc_types(session, user, proj.id)


def test_default_customer_policy_scopes_doc_types():
    customer = next(spec for spec in DEFAULT_POLICIES if spec["name"] == "External Reader")
    assert customer["base_role"] == "external"
    assert set(customer["doc_tag_scope"]) == {"REQ", "TC", "CPT", "CMP"}
