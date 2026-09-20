"""Artefacts are addressable by public id as well as database id (KAN-41, additive)."""

import json

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.artefact_utils import build_related_response, get_artefact_or_404
from app.core.database import Base
from app.models import ArtefactLink, Defect, Project, Requirement, TestCase
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def env():
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
        req = Requirement(
            project_id=project.id, req_id="ALP-REQ-001", title="Login works", status="Approved"
        )
        tc = TestCase(project_id=project.id, tc_id="ALP-TC-001", title="Verify login")
        defect = Defect(project_id=project.id, defect_id="ALP-DEF-001", title="Login broken")
        db.add_all([req, tc, defect])
        await db.flush()
        db.add(
            ArtefactLink(
                project_id=project.id,
                source_type="DEF",
                source_id=defect.id,
                target_type="REQ",
                target_id=req.id,
                role="relates",
            )
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _admin(db):
    return (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()


async def _pk(db, model, id_col, value):
    return (await db.execute(select(model).where(id_col == value))).scalar_one().id


async def test_resolves_by_public_id(env):
    tc = await get_artefact_or_404(env, "test-case", "ALP-TC-001", await _admin(env))
    assert tc.tc_id == "ALP-TC-001"


async def test_resolves_by_database_id_still_works(env):
    tc_pk = await _pk(env, TestCase, TestCase.tc_id, "ALP-TC-001")
    tc = await get_artefact_or_404(env, "test-case", str(tc_pk), await _admin(env))
    assert tc.id == tc_pk


async def test_unknown_public_id_404(env):
    with pytest.raises(HTTPException) as exc:
        await get_artefact_or_404(env, "test-case", "ALP-TC-999", await _admin(env))
    assert exc.value.status_code == 404


async def test_backlinks_identical_by_public_id_and_db_id(env):
    admin = await _admin(env)
    defect_pk = await _pk(env, Defect, Defect.defect_id, "ALP-DEF-001")
    by_public = await build_related_response(env, "defect", "ALP-DEF-001", admin)
    by_pk = await build_related_response(env, "defect", str(defect_pk), admin)
    assert by_public.model_dump() == by_pk.model_dump()
    # the linked requirement resolves either way, so backlinks work by public id
    assert "ALP-REQ-001" in json.dumps(by_public.model_dump(), default=str)
