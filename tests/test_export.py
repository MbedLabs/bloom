"""Tests for CSV/PDF export endpoints (app/api/export.py)."""

import csv
import io

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.export import export_requirements, export_traceability
from app.core.database import Base
from app.models import ArtefactLink, Project, Requirement, TestCase
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

        parent = Requirement(
            project_id=project.id,
            req_id="ALP-REQ-001",
            title="Login shall be possible",
            description="Users must be able to log in.",
            status="Approved",
        )
        db.add(parent)
        await db.flush()
        db.add(
            Requirement(
                project_id=project.id,
                req_id="ALP-REQ-002",
                title="Uncovered requirement",
                parent_id=parent.id,
            )
        )
        tc = TestCase(
            project_id=project.id,
            tc_id="ALP-TC-001",
            title="Verify login",
            last_execution_status="passed",
        )
        db.add(tc)
        await db.flush()
        db.add(
            ArtefactLink(
                project_id=project.id,
                source_type="TC",
                source_id=tc.id,
                target_type="REQ",
                target_id=parent.id,
                role="verifies",
            )
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _admin(db):
    return (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()


def _parse_csv(response) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response.body.decode("utf-8"))))


async def test_requirements_csv_contains_rows_and_parent_ref(session):
    admin = await _admin(session)
    response = await export_requirements(project_id=1, format="csv", db=session, current_user=admin)
    assert response.media_type.startswith("text/csv")
    assert 'filename="ALP-requirements.csv"' in response.headers["content-disposition"]

    rows = _parse_csv(response)
    assert rows[0][:4] == ["req_id", "title", "status", "priority"]
    by_id = {r[0]: r for r in rows[1:]}
    assert by_id["ALP-REQ-001"][1] == "Login shall be possible"
    assert by_id["ALP-REQ-001"][2] == "Approved"
    # child row references its parent by human id, not database pk
    parent_col = rows[0].index("parent_req_id")
    assert by_id["ALP-REQ-002"][parent_col] == "ALP-REQ-001"


async def test_requirements_pdf_is_valid_pdf(session):
    admin = await _admin(session)
    response = await export_requirements(project_id=1, format="pdf", db=session, current_user=admin)
    assert response.media_type == "application/pdf"
    assert response.body[:5] == b"%PDF-"
    assert len(response.body) > 800  # a real document, not an empty shell


async def test_traceability_csv_marks_coverage(session):
    admin = await _admin(session)
    response = await export_traceability(project_id=1, db=session, current_user=admin)
    rows = _parse_csv(response)
    assert rows[0] == [
        "req_id",
        "req_title",
        "req_status",
        "covered",
        "tc_id",
        "tc_title",
        "tc_last_execution",
    ]
    data = {(r[0], r[3]): r for r in rows[1:]}
    covered = data[("ALP-REQ-001", "yes")]
    assert covered[4] == "ALP-TC-001"
    assert covered[6] == "passed"
    uncovered = data[("ALP-REQ-002", "no")]
    assert uncovered[4] == ""  # gap visible in the same file


async def test_export_missing_project_404(session):
    admin = await _admin(session)
    with pytest.raises(HTTPException) as exc:
        await export_requirements(project_id=99, format="csv", db=session, current_user=admin)
    assert exc.value.status_code == 404
