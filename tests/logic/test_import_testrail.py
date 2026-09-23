"""TestRail import endpoint: cases, suites, requirement links, and idempotent re-import."""

import io
import json

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

from app.api.import_service import import_testrail
from app.api.import_service import testrail_csv_columns as columns_endpoint
from app.core.database import Base
from app.models import ArtefactLink, Project, Requirement
from app.models import TestCase as TestCaseModel
from app.models import TestSuite, TestSuiteItem
from app.models.user import User, UserRole
from tests.logic.test_testrail import SEPARATED_CSV, SUITE_XML


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        project = Project(name="Alpha", prefix="ALP")
        db.add(project)
        db.add(
            User(
                email="admin@test.local",
                full_name="Ada Admin",
                hashed_password="x",
                role=UserRole.admin,
            )
        )
        await db.flush()
        db.add(Requirement(project_id=project.id, req_id="ALP-REQ-001", title="Boot fast"))
        await db.commit()
        yield db
    await engine.dispose()


async def _admin(db):
    return (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()


def _upload(content: bytes) -> UploadFile:
    return UploadFile(io.BytesIO(content))


async def _import(db, content, fmt="xml", mapping=None):
    return await import_testrail(
        project_id=1,
        format=fmt,
        file=_upload(content),
        mapping=mapping,
        db=db,
        current_user=await _admin(db),
    )


async def test_xml_import_creates_cases_suite_and_links(session):
    result = await _import(session, SUITE_XML)

    assert (result.created, result.updated, result.skipped) == (2, 0, 0)
    assert result.links_created == 1
    assert len(result.suites_created) == 1
    cold = (
        await session.execute(select(TestCaseModel).where(TestCaseModel.title == "Cold boot"))
    ).scalar_one()
    assert cold.source_ref == "testrail:C7"
    assert cold.status == "Draft"
    assert cold.reviewer_id is None and cold.approver_id is None
    assert cold.preconditions == "Relay open\n\nSerial console attached"
    assert [r["row_type"] for r in cold.steps] == ["precondition", "precondition", "step", "step"]
    assert cold.description == (
        "Imported from TestRail case C7. Type: Functional. Priority: High. Estimate: 5m. "
        "References: JIRA-9."
    )
    link = (await session.execute(select(ArtefactLink))).scalar_one()
    assert (link.source_type, link.source_id, link.target_type, link.role) == (
        "TC",
        cold.id,
        "REQ",
        "verifies",
    )
    suite = (await session.execute(select(TestSuite))).scalar_one()
    assert suite.name == "Boot" and suite.suite_id == result.suites_created[0]
    items = (await session.execute(select(TestSuiteItem))).scalars().all()
    assert len(items) == 2


async def test_reimport_updates_instead_of_duplicating(session):
    await _import(session, SUITE_XML)
    again = await _import(session, SUITE_XML)

    assert (again.created, again.updated) == (0, 2)
    assert again.suites_created == [] and again.links_created == 0
    assert len((await session.execute(select(TestCaseModel))).scalars().all()) == 2
    assert len((await session.execute(select(TestSuiteItem))).scalars().all()) == 2
    assert len((await session.execute(select(ArtefactLink))).scalars().all()) == 1


async def test_csv_import(session):
    result = await _import(session, SEPARATED_CSV, fmt="csv")
    assert (result.created, result.links_created) == (2, 1)
    names = sorted(s.name for s in (await session.execute(select(TestSuite))).scalars().all())
    assert names == ["Firmware"]


async def test_csv_import_with_a_column_mapping(session):
    data = b"Name,Do,Expect\nCold boot,Close relay,Closed\n"
    mapping = json.dumps({"title": "Name", "steps": "Do", "expected": "Expect"})
    result = await _import(session, data, fmt="csv", mapping=mapping)
    assert result.created == 1
    tc = (await session.execute(select(TestCaseModel))).scalar_one()
    assert [(r["description"], r["expected_result"]) for r in tc.steps] == [
        ("Close relay", "Closed")
    ]


async def test_errors(session):
    with pytest.raises(HTTPException) as bad_json:
        await _import(session, SEPARATED_CSV, fmt="csv", mapping="{not json")
    assert bad_json.value.status_code == 422
    with pytest.raises(HTTPException) as bad_file:
        await _import(session, b"<cases/>")
    assert bad_file.value.status_code == 422
    assert "no <suite>" in bad_file.value.detail
    with pytest.raises(HTTPException) as no_title:
        await _import(session, b"Name\nx\n", fmt="csv")
    assert "no Title column" in no_title.value.detail


async def test_missing_title_is_skipped(session):
    xml = b"<suite><cases><case><id>C1</id><title></title></case></cases></suite>"
    result = await _import(session, xml)
    assert (result.created, result.skipped) == (0, 1)
    assert result.errors == ["case C1: missing title"]


async def test_csv_columns_preview(session):
    preview = await columns_endpoint(
        project_id=1, file=_upload(SEPARATED_CSV), db=session, current_user=await _admin(session)
    )
    assert preview.columns[:2] == ["ID", "Title"]
    assert preview.detected["section_hierarchy"] == "Section Hierarchy"
