"""Markdown import endpoint: parameters, the action a name collision requires, and artefacts."""

import io
import json

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

from app.api.import_service import import_markdown
from app.core.database import Base
from app.core.md_import import rename_parameters
from app.models import DesignItem, Notification, Project, ProjectVariable, Requirement
from app.models import TestCase as TestCaseModel
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
    "## [REQ] Fast boot\n"
    "Boot within {{parameter: BOOT_MS, value: 500}} ms\n"
    "## [DES] Boot design\n"
    "Greets with {{parameter: NEW_ONE, value: hello}}\n"
).encode()


async def _import(db, content, actions=None):
    return await import_markdown(
        project_id=1,
        default_type=None,
        file=_upload(content),
        collision_actions=json.dumps(actions) if actions is not None else None,
        db=db,
        current_user=await _admin(db),
    )


async def _count(db, model):
    return len((await db.execute(select(model))).scalars().all())


async def test_a_collision_blocks_the_import_until_an_action_is_chosen(session):
    with pytest.raises(HTTPException) as blocked:
        await _import(session, MD)
    assert blocked.value.status_code == 409
    assert blocked.value.detail["collisions"] == [
        {"name": "BOOT_MS", "existing_value": "old", "imported_value": "500"}
    ]
    assert await _count(session, Requirement) == 0
    assert await _count(session, ProjectVariable) == 1


async def test_keeping_the_existing_value(session):
    result = await _import(session, MD, {"BOOT_MS": {"action": "existing"}})
    assert (result.parameters_created, result.parameter_collisions) == (1, ["BOOT_MS"])
    assert result.parameters_renamed == {}
    boot = (
        await session.execute(select(ProjectVariable).where(ProjectVariable.key == "BOOT_MS"))
    ).scalar_one()
    assert boot.value == "old"
    new = (
        await session.execute(select(ProjectVariable).where(ProjectVariable.key == "NEW_ONE"))
    ).scalar_one()
    assert new.value == "hello"
    sections = {s.title: s.type_code for s in result.sections}
    assert sections == {"Fast boot": "REQ", "Boot design": "DES"}
    assert result.artefacts_created == 2
    req = (
        await session.execute(select(Requirement).where(Requirement.title == "Fast boot"))
    ).scalar_one()
    assert req.req_id.startswith("ALP-REQ-")
    assert req.description == "Boot within {{BOOT_MS}} ms"
    des = (
        await session.execute(select(DesignItem).where(DesignItem.title == "Boot design"))
    ).scalar_one()
    assert des.description == "Greets with {{NEW_ONE}}"
    assert result.notifications_created == 2
    notes = (await session.execute(select(Notification))).scalars().all()
    assert any("Check the necessity" in (n.body or "") for n in notes)


async def test_importing_under_a_new_name(session):
    md = MD + b"The budget {{BOOT_MS}} applies twice.\n"
    result = await _import(session, md, {"boot_ms": {"action": "rename", "to": "BOOT_MS_V2"}})
    assert result.parameters_renamed == {"BOOT_MS": "BOOT_MS_V2"}
    assert result.parameter_collisions == []
    assert result.parameters_created == 2
    values = {v.key: v.value for v in (await session.execute(select(ProjectVariable))).scalars()}
    assert values == {"BOOT_MS": "old", "BOOT_MS_V2": "500", "NEW_ONE": "hello"}
    req = (
        await session.execute(select(Requirement).where(Requirement.title == "Fast boot"))
    ).scalar_one()
    assert req.description == "Boot within {{BOOT_MS_V2}} ms"
    des = (
        await session.execute(select(DesignItem).where(DesignItem.title == "Boot design"))
    ).scalar_one()
    assert "The budget {{BOOT_MS_V2}} applies twice." in des.description


async def test_a_collision_with_a_parameter_of_either_kind(session):
    session.add(ProjectVariable(project_id=1, kind="parameter", key="LIMIT", value="9"))
    await session.commit()
    md = b"## [REQ] Limit\nStay under {{parameter: limit, value: 5}}\n"
    with pytest.raises(HTTPException) as blocked:
        await _import(session, md)
    assert blocked.value.detail["collisions"][0]["existing_value"] == "9"


async def test_rejected_actions(session):
    for actions, expected in (
        ({"BOOT_MS": {"action": "rename", "to": "NEW_ONE"}}, "already taken"),
        ({"BOOT_MS": {"action": "rename", "to": "BOOT_MS"}}, "already taken"),
        ({"BOOT_MS": {"action": "rename", "to": "BAD, NAME"}}, "not a valid parameter name"),
        ({"BOOT_MS": {"action": "delete"}}, "Choose 'existing' or 'rename'"),
        (["BOOT_MS"], "must be an object"),
    ):
        with pytest.raises(HTTPException) as refused:
            await _import(session, MD, actions)
        assert refused.value.status_code == 422
        assert expected in refused.value.detail
    with pytest.raises(HTTPException) as broken:
        await import_markdown(
            project_id=1,
            default_type=None,
            file=_upload(MD),
            collision_actions="{not json",
            db=session,
            current_user=await _admin(session),
        )
    assert "not valid JSON" in broken.value.detail
    assert await _count(session, Requirement) == 0


async def test_no_collision_creates_all(session):
    md = b"## [REQ] Fresh\nUses {{parameter: FRESH_A, value: 1}} and {{parameter: FRESH_B, value: 2}}\n"
    result = await _import(session, md)
    assert result.parameters_created == 2
    assert result.parameter_collisions == []


def test_rename_parameters_rewrites_both_forms():
    text = "A {{parameter: X, value: 1}} and {{ x }} and {{Y}} and {{parameter: Y, value: 2}}"
    assert rename_parameters(text, {"x": "X2"}) == (
        "A {{parameter: X2, value: 1}} and {{X2}} and {{Y}} and {{parameter: Y, value: 2}}"
    )


async def test_test_case_imports_with_step_rows(session):
    md = (
        b"## [TC] Relay boot\n"
        b"Checks the relay-driven boot.\n"
        b"- Pre-Condition: relay open\n"
        b"- Step: close the relay => boot banner within {{parameter: RELAY_MS, value: 200}} ms\n"
    )
    result = await _import(session, md)
    assert result.artefacts_created == 1
    tc = (
        await session.execute(select(TestCaseModel).where(TestCaseModel.title == "Relay boot"))
    ).scalar_one()
    assert tc.tc_id.startswith("ALP-TC-")
    assert tc.description == "Checks the relay-driven boot."
    assert [(r["row_type"], r["description"], r["expected_result"]) for r in tc.steps] == [
        ("precondition", "relay open", ""),
        ("step", "close the relay", "boot banner within {{RELAY_MS}} ms"),
    ]
