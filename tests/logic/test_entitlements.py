"""Project admission, group policies and explicit replacements enforce complete rules."""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.security import (
    access_terms,
    creation_covered,
    customer_only,
    require_project_access,
    row_allows,
    user_can_access_project,
)
from app.models import Project, ProjectMembership, Requirement, User, UserRole
from app.models.groups import Group, GroupMembership, Policy
from app.models.project_membership import ProjectAccess
from tests.access_fixtures import scenario_type_tags


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        yield db
    await engine.dispose()


async def _setup(db, role=UserRole.maintainer):
    user = User(email="user@example.com", full_name="User", hashed_password="x", role=role)
    project = Project(name="Project", prefix="PRJ")
    other = Project(name="Other", prefix="OTH")
    db.add_all([user, project, other])
    await db.flush()
    return user, project, other


async def _policy(db, name, permissions, visibility="internal", types=None):
    policy = Policy(
        name=name,
        permissions=permissions,
        type_tags=scenario_type_tags(permissions, visibility, types),
    )
    db.add(policy)
    await db.flush()
    return policy


async def _group(db, user, project, policies):
    group = Group(name="Team", policies=policies)
    db.add(group)
    await db.flush()
    membership = GroupMembership(group_id=group.id, user_id=user.id)
    db.add_all(
        [membership, ProjectAccess(group_id=group.id, project_id=project.id, inherit_policies=True)]
    )
    await db.flush()
    return membership


@pytest.mark.asyncio
async def test_group_grant_reaches_only_its_explicit_project(session):
    user, project, other = await _setup(session)
    policy = await _policy(session, "Read", {"REQ": ["view"]})
    await _group(session, user, project, [policy])
    assert await user_can_access_project(session, user, project.id)
    assert not await user_can_access_project(session, user, other.id)


@pytest.mark.asyncio
async def test_no_grant_has_no_access(session):
    user, project, _ = await _setup(session)
    with pytest.raises(HTTPException) as error:
        await require_project_access(session, user, project.id)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_instance_admin_access_is_independent_of_project_entries(session):
    user, project, _ = await _setup(session, UserRole.admin)
    assert await user_can_access_project(session, user, project.id)


@pytest.mark.asyncio
async def test_a_membership_row_or_a_group_without_an_entry_grants_no_access(session):
    user, project, _ = await _setup(session)
    group = Group(name="Old team")
    session.add(group)
    await session.flush()
    session.add_all(
        [
            ProjectMembership(user_id=user.id, project_id=project.id, role="maintainer"),
            GroupMembership(group_id=group.id, user_id=user.id),
        ]
    )
    await session.flush()
    assert not await user_can_access_project(session, user, project.id)


@pytest.mark.asyncio
async def test_removing_group_membership_keeps_independent_direct_grant(session):
    user, project, _ = await _setup(session)
    read = await _policy(session, "Read", {"REQ": ["view"]})
    write = await _policy(session, "Write", {"REQ": ["edit"]})
    session.add(ProjectAccess(user_id=user.id, project_id=project.id, policies=[read]))
    membership = await _group(session, user, project, [write])
    assert all(
        "edit" not in term.permissions["REQ"]
        for term in await access_terms(session, user, project.id)
    )
    await session.delete(membership)
    await session.flush()
    del user.access_map
    terms = await access_terms(session, user, project.id)
    assert len(terms) == 1
    assert terms[0].permissions == {"REQ": {"view"}}


@pytest.mark.asyncio
async def test_broad_read_does_not_lend_visibility_to_scoped_write(session):
    user, project, _ = await _setup(session)
    read = await _policy(session, "Broad read", {"REQ": ["view"]})
    write = await _policy(session, "Customer write", {"REQ": ["edit"]}, "customer", ["REQ"])
    await _group(session, user, project, [read, write])
    internal = Requirement(
        project_id=project.id, req_id="PRJ-REQ-001", title="Internal", visibility="internal"
    )
    customer = Requirement(
        project_id=project.id, req_id="PRJ-REQ-002", title="Customer", visibility="customer"
    )
    session.add_all([internal, customer])
    await session.flush()
    assert await row_allows(session, user, internal, "view", "REQ")
    assert not await row_allows(session, user, internal, "edit", "REQ")
    assert await row_allows(session, user, customer, "edit", "REQ")


@pytest.mark.asyncio
async def test_document_type_scope_keeps_explicit_link_permission(session):
    user, project, _ = await _setup(session)
    policy = await _policy(
        session, "Requirement links", {"REQ": ["view"], "link": ["create"]}, types=["REQ"]
    )
    await _group(session, user, project, [policy])
    await require_project_access(session, user, project.id, permission=("create", "link"))
    with pytest.raises(HTTPException):
        await require_project_access(session, user, project.id, permission=("view", "TC"))


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", [False, True])
async def test_external_project_grants_do_not_expose_parameters(session, owner):
    user, project, _ = await _setup(session, UserRole.external)
    policies = []
    if not owner:
        policies.append(await _policy(session, "Parameter grant", {"parameter": ["view"]}))
    session.add(
        ProjectAccess(user_id=user.id, project_id=project.id, owner=owner, policies=policies)
    )
    await session.flush()
    with pytest.raises(HTTPException) as denied:
        await require_project_access(session, user, project.id, permission=("view", "parameter"))
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_owner_is_a_direct_project_entry_and_does_not_change_instance_role(session):
    user, project, other = await _setup(session)
    session.add(ProjectAccess(user_id=user.id, project_id=project.id, owner=True))
    await session.flush()
    assert await user_can_access_project(session, user, project.id)
    assert not await user_can_access_project(session, user, other.id)
    assert user.role == UserRole.maintainer
    assert any(
        term.permissions == {"*": {"*"}} for term in await access_terms(session, user, project.id)
    )


@pytest.mark.asyncio
async def test_customer_scope_does_not_change_account_identity(session):
    internal, project, _ = await _setup(session)
    policy = await _policy(session, "Customer scope", {"REQ": ["view"]}, "customer")
    session.add(ProjectAccess(user_id=internal.id, project_id=project.id, policies=[policy]))
    await session.flush()
    await access_terms(session, internal, project.id)
    assert not customer_only(internal)
    external = User(
        email="external@example.com",
        full_name="External",
        hashed_password="x",
        role=UserRole.external,
    )
    session.add(external)
    await session.flush()
    session.add(ProjectAccess(user_id=external.id, project_id=project.id, policies=[policy]))
    await session.flush()
    assert customer_only(external)


@pytest.mark.asyncio
async def test_external_identity_preserves_customer_only_reading_with_broad_policy(session):
    user, project, _ = await _setup(session, UserRole.external)
    policy = await _policy(session, "Broad read", {"REQ": ["view"]}, "internal")
    session.add(ProjectAccess(user_id=user.id, project_id=project.id, policies=[policy]))
    internal = Requirement(
        project_id=project.id, req_id="PRJ-REQ-001", title="Internal", visibility="internal"
    )
    customer = Requirement(
        project_id=project.id, req_id="PRJ-REQ-002", title="Customer", visibility="customer"
    )
    session.add_all([internal, customer])
    await session.flush()
    assert not await row_allows(session, user, internal, "view", "REQ")
    assert await row_allows(session, user, customer, "view", "REQ")
    from sqlalchemy import select

    from app.core.security import apply_external_visibility_filter

    rows = (
        (
            await session.execute(
                apply_external_visibility_filter(select(Requirement), Requirement, user)
            )
        )
        .scalars()
        .all()
    )
    assert [row.id for row in rows] == [customer.id]


@pytest.mark.asyncio
async def test_a_kept_matrix_approves_only_rows_its_approving_policy_covers(session):
    user, project, _ = await _setup(session)
    author = await _policy(session, "Author", {"REQ": ["view", "create"]})
    signer = await _policy(session, "Signer", {"REQ": ["view", "approve"]}, "customer")
    session.add(ProjectAccess(user_id=user.id, project_id=project.id, policies=[author, signer]))
    await session.flush()
    for visibility in ("internal", "customer"):
        assert await creation_covered(session, user, project.id, "REQ", visibility, [])
    assert not await creation_covered(session, user, project.id, "REQ", "internal", [], "approve")
    assert await creation_covered(session, user, project.id, "REQ", "customer", [], "approve")


@pytest.mark.asyncio
async def test_write_reading_stays_within_its_resource_and_origin(session):
    user, project, _ = await _setup(session)
    write = await _policy(session, "Customer author", {"REQ": ["edit"]}, "customer", ["REQ"])
    await _group(session, user, project, [write])
    customer = Requirement(
        project_id=project.id, req_id="PRJ-REQ-001", title="Customer", visibility="customer"
    )
    internal = Requirement(
        project_id=project.id, req_id="PRJ-REQ-002", title="Internal", visibility="internal"
    )
    session.add_all([customer, internal])
    await session.flush()
    assert await row_allows(session, user, customer, "view", "REQ")
    assert await row_allows(session, user, customer, "edit", "REQ")
    assert not await row_allows(session, user, customer, "approve", "REQ")
    assert not await row_allows(session, user, customer, "delete", "REQ")
    assert not await row_allows(session, user, internal, "view", "REQ")
    assert not await row_allows(session, user, customer, "view", "TC")


@pytest.mark.asyncio
@pytest.mark.parametrize("external", [False, True])
async def test_overlapping_bundle_operations_keep_their_own_origins_and_account_caps(
    session, external
):
    user, project, other = await _setup(
        session, UserRole.external if external else UserRole.maintainer
    )
    read = await _policy(session, "Read all", {"REQ": ["view"]})
    write = await _policy(
        session, "Customer author", {"REQ": ["edit", "approve", "delete"]}, "customer"
    )
    bundles = [Group(name="Readers", policies=[read]), Group(name="Authors", policies=[write])]
    session.add_all(bundles)
    await session.flush()
    session.add_all(
        [
            ProjectAccess(user_id=user.id, project_id=project.id, policy_group=bundle)
            for bundle in bundles
        ]
    )
    customer = Requirement(
        project_id=project.id, req_id="PRJ-REQ-001", title="Customer", visibility="customer"
    )
    internal = Requirement(
        project_id=project.id, req_id="PRJ-REQ-002", title="Internal", visibility="internal"
    )
    session.add_all([customer, internal])
    await session.flush()
    assert await row_allows(session, user, customer, "view", "REQ")
    assert await row_allows(session, user, customer, "edit", "REQ")
    assert not await row_allows(session, user, internal, "edit", "REQ")
    assert await row_allows(session, user, internal, "view", "REQ") is not external
    assert await row_allows(session, user, customer, "approve", "REQ") is not external
    assert await row_allows(session, user, customer, "delete", "REQ") is not external
    assert not await user_can_access_project(session, user, other.id)


@pytest.mark.asyncio
async def test_overlapping_bundles_do_not_borrow_another_policys_tag_scope(session):
    user, project, _ = await _setup(session)
    read = await _policy(session, "Unrestricted read", {"REQ": ["view"]})
    read.type_tags = {"REQ": {"all": True}}
    write = await _policy(session, "Chosen tag write", {"REQ": ["edit"]})
    write.type_tags = {"REQ": {"tags": [101]}}
    bundles = [Group(name="Readers", policies=[read]), Group(name="Authors", policies=[write])]
    session.add_all(bundles)
    await session.flush()
    session.add_all(
        [
            ProjectAccess(user_id=user.id, project_id=project.id, policy_group=bundle)
            for bundle in bundles
        ]
    )
    await session.flush()
    assert await creation_covered(session, user, project.id, "REQ", "internal", [202], "view")
    assert not await creation_covered(session, user, project.id, "REQ", "internal", [202], "edit")
    assert await creation_covered(session, user, project.id, "REQ", "internal", [101], "edit")
