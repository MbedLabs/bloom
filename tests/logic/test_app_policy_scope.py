"""Group app rules and admitted project content retain independent scope boundaries."""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.security import access_terms, effective_permissions, require_role
from app.models import Project, User, UserRole
from app.models.groups import Group, GroupMembership, Policy
from app.models.project_membership import ProjectAccess


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        yield db
    await engine.dispose()


async def _setup(db, role=UserRole.maintainer, scope="app"):
    user = User(email="scope@example.com", full_name="Scope", hashed_password="x", role=role)
    project = Project(name="Scope", prefix="SCP")
    policy = Policy(
        name="Application rules",
        scope=scope,
        permissions={
            "users": ["view", "create", "edit"],
            "access": ["delete"],
            "REQ": ["view", "edit"],
            "project": ["view"],
        },
        type_tags={"REQ": {"all": True}},
    )
    group = Group(name="Scope group", policies=[policy])
    db.add_all([user, project, group])
    await db.flush()
    db.add(GroupMembership(user_id=user.id, group_id=group.id))
    await db.flush()
    return user, project, group


@pytest.mark.asyncio
async def test_group_app_rules_apply_without_project_admission(session):
    user, project, _ = await _setup(session)
    terms = await access_terms(session, user, None)
    assert {resource for term in terms for resource in term.permissions} == {"users", "access"}
    assert await effective_permissions(session, user, None) == {
        "users": {"view", "create", "edit"},
        "access": {"delete"},
    }
    assert await access_terms(session, user, project.id) == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["document", "project"])
async def test_other_policy_scopes_do_not_supply_global_app_terms(session, scope):
    user, _, _ = await _setup(session, scope=scope)
    assert await access_terms(session, user, None) == ()


@pytest.mark.asyncio
async def test_app_content_rules_require_admission_and_never_include_app_resources(session):
    user, project, group = await _setup(session)
    session.add(ProjectAccess(project_id=project.id, group_id=group.id, inherit_policies=True))
    await session.flush()
    permissions = await effective_permissions(session, user, project.id)
    assert permissions == {"REQ": {"view", "comment", "edit"}, "project": {"view"}}


@pytest.mark.asyncio
async def test_project_replacement_does_not_replace_global_app_rules(session):
    user, project, group = await _setup(session)
    replacement = Policy(
        name="Project read",
        scope="document",
        permissions={"REQ": ["view"]},
        type_tags={"REQ": {"all": True}},
    )
    session.add_all(
        [
            ProjectAccess(project_id=project.id, group_id=group.id, inherit_policies=True),
            ProjectAccess(project_id=project.id, user_id=user.id, policies=[replacement]),
        ]
    )
    await session.flush()
    assert await effective_permissions(session, user, project.id) == {"REQ": {"view"}}
    assert await effective_permissions(session, user, None) == {
        "users": {"view", "create", "edit"},
        "access": {"delete"},
    }


@pytest.mark.asyncio
async def test_configured_app_rules_do_not_open_admin_only_management(session):
    user, _, _ = await _setup(session)
    assert (await effective_permissions(session, user, None))["users"] == {"view", "create", "edit"}
    admin_only = require_role(UserRole.admin)
    with pytest.raises(HTTPException) as refused:
        await admin_only(user)
    assert refused.value.status_code == 403


@pytest.mark.asyncio
async def test_instance_admin_keeps_global_authority_without_policy_assignment(session):
    user = User(
        email="admin-scope@example.com", full_name="Admin", hashed_password="x", role=UserRole.admin
    )
    session.add(user)
    await session.flush()
    assert await effective_permissions(session, user, None) == {"*": {"*"}}


@pytest.mark.asyncio
async def test_multiple_direct_bundles_combine_without_restoring_indirect_project_rights(session):
    user, project, inherited = await _setup(session)
    first = Policy(
        name="Direct requirements", permissions={"REQ": ["view"]}, type_tags={"REQ": {"all": True}}
    )
    second = Policy(
        name="Direct tests", permissions={"TC": ["edit"]}, type_tags={"TC": {"all": True}}
    )
    bundles = [Group(name="Readers", policies=[first]), Group(name="Testers", policies=[second])]
    session.add_all(bundles)
    await session.flush()
    session.add_all(
        [
            ProjectAccess(project_id=project.id, group_id=inherited.id, inherit_policies=True),
            *[
                ProjectAccess(project_id=project.id, user_id=user.id, policy_group=bundle)
                for bundle in bundles
            ],
        ]
    )
    await session.flush()
    permissions = await effective_permissions(session, user, project.id)
    assert permissions == {"REQ": {"view"}, "TC": {"view", "comment", "edit"}}
    assert "project" not in permissions
    assert (await effective_permissions(session, user, None))["access"] == {"delete"}
