"""Tests for the global search endpoint (app/api/search.py)."""

import pytest
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


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        alpha = Project(name="Alpha", prefix="ALP")
        beta = Project(name="Beta", prefix="BET")
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
                    req_id="ALP-REQ-001",
                    title="Login shall be possible",
                    visibility=ArtefactVisibility.customer.value,
                ),
                Requirement(
                    project_id=alpha.id,
                    req_id="ALP-REQ-002",
                    title="Internal crypto module",
                    visibility=ArtefactVisibility.internal.value,
                ),
                Requirement(
                    project_id=beta.id,
                    req_id="BET-REQ-001",
                    title="Login for Beta",
                ),
                TestCase(
                    project_id=alpha.id,
                    tc_id="ALP-TC-001",
                    title="Verify login flow",
                    visibility=ArtefactVisibility.customer.value,
                ),
                Document(project_id=alpha.id, doc_id="ALP-SPEC-001", title="Login spec"),
                Defect(
                    project_id=alpha.id,
                    defect_id="ALP-DEF-001",
                    title="Login button broken",
                ),
                TestSuite(project_id=alpha.id, suite_id="ALP-TS-001", name="Login suite"),
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
    assert ("REQ", "ALP-REQ-001") in types
    assert ("REQ", "BET-REQ-001") in types  # cross-project
    assert ("TC", "ALP-TC-001") in types
    assert ("SPEC", "ALP-SPEC-001") in types  # Document reports its own doc_type
    assert ("DEF", "ALP-DEF-001") in types
    assert ("TS", "ALP-TS-001") in types


async def test_exact_id_match_ranks_first(session):
    admin = await _user(session, UserRole.admin)
    res = await run_global_search(session, admin, q="ALP-REQ-001")
    assert res.items, "expected results"
    assert res.items[0].doc_id == "ALP-REQ-001"


async def test_project_filter_narrows_results(session):
    admin = await _user(session, UserRole.admin)
    beta_id = (
        await session.execute(select(Project.id).where(Project.prefix == "BET"))
    ).scalar_one()
    res = await run_global_search(session, admin, q="login", project_id=beta_id)
    assert {i.project_prefix for i in res.items} == {"BET"}


async def test_member_sees_only_member_projects(session):
    member = await _user(session, UserRole.maintainer)
    alpha_id = (
        await session.execute(select(Project.id).where(Project.prefix == "ALP"))
    ).scalar_one()
    session.add(ProjectMembership(user_id=member.id, project_id=alpha_id, role="maintainer"))
    await session.commit()

    res = await run_global_search(session, member, q="login")
    assert res.items, "member should see Alpha artefacts"
    assert {i.project_prefix for i in res.items} == {"ALP"}


async def test_member_without_membership_sees_nothing(session):
    member = await _user(session, UserRole.maintainer)
    res = await run_global_search(session, member, q="login")
    assert res.total == 0 and res.items == []


async def test_external_gated_by_doc_type_and_visibility(session):
    ext = await _user(session, UserRole.external)
    alpha_id = (
        await session.execute(select(Project.id).where(Project.prefix == "ALP"))
    ).scalar_one()
    membership = ProjectMembership(user_id=ext.id, project_id=alpha_id, role="external")
    session.add(membership)
    await session.flush()
    session.add(ProjectExternalDocType(membership_id=membership.id, doc_type="REQ"))
    await session.commit()

    res = await run_global_search(session, ext, q="login")
    # Only customer-visible REQs: not the internal crypto REQ, not TC/DOC/DEF/TS
    assert {(i.type, i.doc_id) for i in res.items} == {("REQ", "ALP-REQ-001")}

    res_internal = await run_global_search(session, ext, q="crypto")
    assert res_internal.total == 0


async def test_external_with_no_allowlist_sees_nothing(session):
    ext = await _user(session, UserRole.external)
    alpha_id = (
        await session.execute(select(Project.id).where(Project.prefix == "ALP"))
    ).scalar_one()
    session.add(ProjectMembership(user_id=ext.id, project_id=alpha_id, role="external"))
    await session.commit()

    res = await run_global_search(session, ext, q="login")
    assert res.total == 0


def test_rank_match_ordering():
    q = "alp-req-001"
    assert rank_match(q, "ALP-REQ-001", "anything") == 0  # exact id
    assert rank_match("alp-req", "ALP-REQ-001", "x") == 1  # id prefix
    assert rank_match("login", "ALP-REQ-001", "Login shall") == 2  # title prefix
    assert rank_match("req-001", "ALP-REQ-001", "x") == 3  # id substring
    assert rank_match("shall", "ALP-REQ-001", "Login shall") == 4  # title substring
    assert rank_match("zzz", "ALP-REQ-001", "Login shall") == 5
