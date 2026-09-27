"""Copying requirements and test cases from one project into another."""

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.import_service import ImportResult, _import_docs, _next_number
from app.core.database import Base
from app.models import Project, Requirement
from app.models import TestCase as TestCaseModel


@pytest_asyncio.fixture
async def projects():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        source = Project(name="Source", prefix="SRC")
        target = Project(name="Target", prefix="DST")
        db.add_all([source, target])
        await db.flush()
        db.add(
            Requirement(
                project_id=source.id,
                req_id="SRC-REQ-001",
                title="Boot",
                description="Boots fast",
                content_json={"k": 1},
                content_html="<p>1</p>",
                status="Approved",
                priority="High",
                req_type="functional",
                req_origin="customer",
            )
        )
        db.add(
            TestCaseModel(
                project_id=source.id,
                tc_id="SRC-TC-001",
                title="Boot test",
                status="Approved",
                preconditions="Powered",
                steps=[{"action": "Power on"}],
            )
        )
        db.add(Requirement(project_id=target.id, req_id="DST-REQ-007", title="Existing"))
        await db.commit()
        yield db, source, target
    await engine.dispose()


def _result() -> ImportResult:
    return ImportResult(imported=0, skipped=0, new_ids=[], errors=[])


async def test_requirements_are_copied_as_drafts_after_the_highest_id(projects):
    db, source, target = projects
    source_ids = [
        r.id
        for r in (
            await db.execute(select(Requirement).where(Requirement.project_id == source.id))
        ).scalars()
    ]
    result = _result()

    await _import_docs(db, "REQ", source_ids + [99999], source, target, result)

    assert (result.imported, result.skipped, result.new_ids) == (1, 1, ["DST-REQ-008"])
    assert result.errors == ["Requirement 99999 not found in source project"]
    copy = (
        await db.execute(select(Requirement).where(Requirement.req_id == "DST-REQ-008"))
    ).scalar_one()
    assert (copy.title, copy.description, copy.priority, copy.req_type, copy.req_origin) == (
        "Boot",
        "Boots fast",
        "High",
        "functional",
        "customer",
    )
    assert (copy.status, copy.source_ref, copy.source_project_id) == (
        "Draft",
        "SRC-REQ-001",
        source.id,
    )
    assert await _next_number(db, target.id, target.prefix, "REQ") == 9


async def test_test_cases_keep_their_steps_and_preconditions(projects):
    db, source, target = projects
    source_ids = [
        t.id
        for t in (
            await db.execute(select(TestCaseModel).where(TestCaseModel.project_id == source.id))
        ).scalars()
    ]
    result = _result()

    await _import_docs(db, "TC", source_ids, source, target, result)

    assert result.new_ids == ["DST-TC-001"]
    copy = (
        await db.execute(select(TestCaseModel).where(TestCaseModel.tc_id == "DST-TC-001"))
    ).scalar_one()
    assert (copy.preconditions, copy.steps, copy.status, copy.source_ref) == (
        "Powered",
        [{"action": "Power on"}],
        "Draft",
        "SRC-TC-001",
    )
