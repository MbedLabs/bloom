"""Markdown import endpoint: parameters (collision requires action) + classification."""

import io

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

from app.api.import_service import import_markdown
from app.core.database import Base
from app.models import DesignItem, Notification, Project, ProjectVariable, Requirement
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
        db.add(ProjectVariable(project_id=project.id, kind="variable", key="BOOT_MS", value="old"))
        await db.commit()
        yield db
    await engine.dispose()


async def _admin(db):
    return (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()


def _upload(content: bytes) -> UploadFile:
    return UploadFile(io.BytesIO(content))


MD = (
    "---\n"
    "type: requirement\n"
    "---\n"
    "## Parameters\n"
    "parameter: BOOT_MS\n"
    "value: 500\n"
    "parameter: NEW_ONE\n"
    "value: hello\n"
    "## [REQ] Fast boot\n"
    "body\n"
    "## [DES] Boot design\n"
    "body2\n"
).encode()


async def test_collision_requires_action_and_never_overwrites(session):
    admin = await _admin(session)
    result = await import_markdown(
        project_id=1, default_type=None, file=_upload(MD), db=session, current_user=admin
    )
    assert result.parameters_created == 1
    assert result.parameter_collisions == ["BOOT_MS"]
    # the existing parameter keeps its old value (no overwrite)
    boot = (
        await session.execute(select(ProjectVariable).where(ProjectVariable.key == "BOOT_MS"))
    ).scalar_one()
    assert boot.value == "old"
    # the new parameter was created
    new = (
        await session.execute(select(ProjectVariable).where(ProjectVariable.key == "NEW_ONE"))
    ).scalar_one()
    assert new.value == "hello"
    # sections classified by tag
    sections = {s.title: s.type_code for s in result.sections}
    assert sections["Fast boot"] == "REQ"
    assert sections["Boot design"] == "DES"
    # the tagged sections became artefacts; the Parameters section did not
    assert result.artefacts_created == 2
    req = (
        await session.execute(select(Requirement).where(Requirement.title == "Fast boot"))
    ).scalar_one()
    assert req.req_id.startswith("ALP-REQ-")
    des = (
        await session.execute(select(DesignItem).where(DesignItem.title == "Boot design"))
    ).scalar_one()
    assert des.design_id.startswith("ALP-DES-")
    # each unlinked artefact prompts the uploader to link it, with the review wording
    assert result.notifications_created == 2
    notes = (await session.execute(select(Notification))).scalars().all()
    assert len(notes) == 2
    assert any("Check the necessity" in (n.body or "") for n in notes)


async def test_no_collision_creates_all(session):
    admin = await _admin(session)
    md = b"## Parameters\nparameter: FRESH_A\nvalue: 1\nparameter: FRESH_B\nvalue: 2\n"
    result = await import_markdown(
        project_id=1, default_type=None, file=_upload(md), db=session, current_user=admin
    )
    assert result.parameters_created == 2
    assert result.parameter_collisions == []
