"""Import test cases from CSV/XML in the export format (round-trip)."""

import io

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

from app.api.test_cases import import_test_cases
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
                project_id=project.id, tc_id="ALP-TC-001", title="Verify login", status="Draft"
            )
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _admin(db):
    return (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()


def _upload(content: bytes) -> UploadFile:
    return UploadFile(io.BytesIO(content))


async def test_csv_import_updates_existing_and_creates_new(session):
    admin = await _admin(session)
    content = (
        "tc_id,title,status,visibility,preconditions,steps,description\n"
        "ALP-TC-001,Updated login,Approved,internal,User exists,1. Open => Form,Round-trip\n"
        ",Brand new case,Draft,internal,,1. Do X => Y,New one\n"
    ).encode()
    result = await import_test_cases(
        project_id=1, format="csv", file=_upload(content), db=session, current_user=admin
    )
    assert result["updated"] == 1
    assert result["created"] == 1
    tc = (
        await session.execute(select(TestCase).where(TestCase.tc_id == "ALP-TC-001"))
    ).scalar_one()
    assert tc.title == "Updated login"
    assert tc.steps == [{"action": "Open", "expected": "Form"}]
    assert (await session.execute(select(TestCase))).scalars().all().__len__() == 2


async def test_xml_import_creates(session):
    admin = await _admin(session)
    xml = (
        b'<?xml version="1.0"?><test-cases>'
        b'<test-case id="X"><title>From XML</title><status>Draft</status>'
        b"<steps>1. Click => Opens</steps></test-case></test-cases>"
    )
    result = await import_test_cases(
        project_id=1, format="xml", file=_upload(xml), db=session, current_user=admin
    )
    assert result["created"] == 1
    tc = (await session.execute(select(TestCase).where(TestCase.title == "From XML"))).scalar_one()
    assert tc.steps == [{"action": "Click", "expected": "Opens"}]
    assert tc.tc_id.startswith("ALP-TC-")


async def test_missing_title_is_skipped(session):
    admin = await _admin(session)
    content = b"tc_id,title,steps\n,,1. x\n"
    result = await import_test_cases(
        project_id=1, format="csv", file=_upload(content), db=session, current_user=admin
    )
    assert result["skipped"] == 1
    assert result["created"] == 0
    assert result["errors"] == ["row 1: missing title"]
