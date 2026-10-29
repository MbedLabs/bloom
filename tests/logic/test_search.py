"""Tests for the global search endpoint (app/api/search.py)."""

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.search import run_global_search
from app.core.database import Base
from app.core.search_registry import rank_match
from app.models import (
    Defect,
    Document,
    Project,
    ProjectExternalDocType,
    ProjectMembership,
    Requirement,
    TestCase,
    TestSuite,
)
from app.models.models import ArtefactVisibility
from app.models.user import User, UserRole
from tests.access_fixtures import allow_doc_types, project_access_fixture


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        alpha = Project(name="Demo", prefix="PRJ")
        beta = Project(name="ABC", prefix="ABC")
        db.add_all([alpha, beta])
        await db.flush()

        db.add_all(
            [
                User(
                    email="admin@test.local",
                    full_name="Ada Admin",
                    hashed_password="x",
                    role=UserRole.admin,
                ),
                User(
                    email="member@test.local",
                    full_name="Mia Maintainer",
                    hashed_password="x",
                    role=UserRole.maintainer,
                ),
                User(
                    email="ext@test.local",
                    full_name="Eve External",
                    hashed_password="x",
                    role=UserRole.external,
                ),
            ]
        )
        await db.flush()

        db.add_all(
            [
                Requirement(
                    project_id=alpha.id,
                    req_id="PRJ-REQ-001",
                    title="Login shall be possible",
                    visibility=ArtefactVisibility.customer.value,
                ),
                Requirement(
                    project_id=alpha.id,
                    req_id="PRJ-REQ-002",
                    title="Internal crypto module",
                    visibility=ArtefactVisibility.internal.value,
                ),
                Requirement(
                    project_id=beta.id,
                    req_id="ABC-REQ-001",
                    title="Login for Beta",
                ),
                TestCase(
                    project_id=alpha.id,
                    tc_id="PRJ-TC-001",
                    title="Verify login flow",
                    visibility=ArtefactVisibility.customer.value,
                ),
                Document(project_id=alpha.id, doc_id="PRJ-SPEC-001", title="Login spec"),
                Defect(
                    project_id=alpha.id,
                    defect_id="PRJ-DEF-001",
                    title="Login button broken",
                ),
                TestSuite(project_id=alpha.id, suite_id="PRJ-TS-001", name="Login suite"),
            ]
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _user(db, role):
    return (await db.execute(select(User).where(User.role == role))).scalar_one()


async def test_admin_searches_all_projects(session):
    admin = await _user(session, UserRole.admin)
    res = await run_global_search(session, admin, q="login")
    types = {(i.type, i.doc_id) for i in res.items}
    assert ("REQ", "PRJ-REQ-001") in types
    assert ("REQ", "ABC-REQ-001") in types
    assert ("TC", "PRJ-TC-001") in types
    assert ("SPEC", "PRJ-SPEC-001") in types
    assert ("DEF", "PRJ-DEF-001") in types
    assert ("TS", "PRJ-TS-001") in types


async def test_exact_id_match_ranks_first(session):
    admin = await _user(session, UserRole.admin)
    res = await run_global_search(session, admin, q="PRJ-REQ-001")
    assert res.items, "expected results"
    assert res.items[0].doc_id == "PRJ-REQ-001"


async def test_project_filter_narrows_results(session):
    admin = await _user(session, UserRole.admin)
    beta_id = (
        await session.execute(select(Project.id).where(Project.prefix == "ABC"))
    ).scalar_one()
    res = await run_global_search(session, admin, q="login", project_id=beta_id)
    assert {i.project_prefix for i in res.items} == {"ABC"}


async def test_member_sees_only_member_projects(session):
    member = await _user(session, UserRole.maintainer)
    alpha_id = (
        await session.execute(select(Project.id).where(Project.prefix == "PRJ"))
    ).scalar_one()
    session.add(
        project_access_fixture(user_id=member.id, project_id=alpha_id, permissions={"*": ["*"]})
    )
    await session.commit()

    res = await run_global_search(session, member, q="login")
    assert res.items, "member should see Alpha artefacts"
    assert {i.project_prefix for i in res.items} == {"PRJ"}


async def test_member_without_membership_sees_nothing(session):
    member = await _user(session, UserRole.maintainer)
    res = await run_global_search(session, member, q="login")
    assert res.total == 0
    assert res.items == []


async def test_external_gated_by_doc_type_and_visibility(session):
    ext = await _user(session, UserRole.external)
    alpha_id = (
        await session.execute(select(Project.id).where(Project.prefix == "PRJ"))
    ).scalar_one()
    membership = project_access_fixture(
        user_id=ext.id,
        project_id=alpha_id,
        permissions={"*": ["view", "comment"]},
        visibility="customer",
        doc_types=[],
    )
    session.add(membership)
    await session.flush()
    allow_doc_types(membership.policies[0], ["REQ"])
    await session.commit()

    res = await run_global_search(session, ext, q="login")
    assert {(i.type, i.doc_id) for i in res.items} == {("REQ", "PRJ-REQ-001")}

    res_internal = await run_global_search(session, ext, q="crypto")
    assert res_internal.total == 0


async def test_external_with_no_allowlist_sees_nothing(session):
    ext = await _user(session, UserRole.external)
    alpha_id = (
        await session.execute(select(Project.id).where(Project.prefix == "PRJ"))
    ).scalar_one()
    session.add(
        project_access_fixture(
            user_id=ext.id,
            project_id=alpha_id,
            permissions={"*": ["view", "comment"]},
            visibility="customer",
            doc_types=[],
        )
    )
    await session.commit()

    res = await run_global_search(session, ext, q="login")
    assert res.total == 0


def test_rank_match_ordering():
    q = "prj-req-001"
    assert rank_match(q, "PRJ-REQ-001", "anything") == 0
    assert rank_match("prj-req", "PRJ-REQ-001", "x") == 1
    assert rank_match("login", "PRJ-REQ-001", "Login shall") == 2
    assert rank_match("req-001", "PRJ-REQ-001", "x") == 3
    assert rank_match("shall", "PRJ-REQ-001", "Login shall") == 4
    assert rank_match("zzz", "PRJ-REQ-001", "Login shall") == 5
