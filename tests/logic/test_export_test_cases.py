"""Tests for the test-case export endpoint (CSV / Markdown / XML)."""

import csv
import io
from xml.etree import ElementTree as ET

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.export import export_test_cases
from app.core.database import Base
from app.models import Project, TestCase
from app.models.user import User, UserRole


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
        db.add(
            TestCase(
                project_id=project.id,
                tc_id="ALP-TC-001",
                title="Verify login",
                status="Approved",
                preconditions="User exists",
                steps=[
                    {"action": "Open login", "expected": "Form shown"},
                    {"action": "Submit", "expected": "Dashboard"},
                ],
                description="Covers the happy path.",
                last_execution_status="passed",
            )
        )
        db.add(
            TestCase(
                project_id=project.id,
                tc_id="ALP-TC-002",
                title="Verify logout",
                status="Draft",
            )
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _admin(db):
    return (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()


async def test_test_cases_csv(session):
    admin = await _admin(session)
    response = await export_test_cases(project_id=1, format="csv", db=session, current_user=admin)
    assert response.media_type.startswith("text/csv")
    assert 'filename="ALP-test-cases.csv"' in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.body.decode("utf-8"))))
    assert rows[0][:3] == ["tc_id", "title", "status"]
    by_id = {r[0]: r for r in rows[1:]}
    assert by_id["ALP-TC-001"][1] == "Verify login"
    steps_col = rows[0].index("steps")
    assert "Open login => Form shown" in by_id["ALP-TC-001"][steps_col]


async def test_test_cases_markdown(session):
    admin = await _admin(session)
    response = await export_test_cases(project_id=1, format="md", db=session, current_user=admin)
    assert response.media_type.startswith("text/markdown")
    assert 'filename="ALP-test-cases.md"' in response.headers["content-disposition"]
    body = response.body.decode("utf-8")
    assert "# Alpha - Test Cases" in body
    assert "## ALP-TC-001  Verify login" in body
    assert "1. Open login => Form shown" in body


async def test_test_cases_xml_is_wellformed(session):
    admin = await _admin(session)
    response = await export_test_cases(project_id=1, format="xml", db=session, current_user=admin)
    assert response.media_type.startswith("application/xml")
    root = ET.fromstring(response.body)
    assert root.tag == "test-cases"
    ids = [tc.get("id") for tc in root.findall("test-case")]
    assert ids == ["ALP-TC-001", "ALP-TC-002"]
    assert root.find("test-case").findtext("title") == "Verify login"


async def test_export_missing_project_404(session):
    admin = await _admin(session)
    with pytest.raises(HTTPException) as exc:
        await export_test_cases(project_id=99, format="csv", db=session, current_user=admin)
    assert exc.value.status_code == 404
