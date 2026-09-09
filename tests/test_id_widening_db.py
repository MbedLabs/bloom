import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.core.id_generator import next_doc_id
from app.models.models import Project, Requirement

"""Widening is applied to the rows, not just computed."""


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        from app import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _project_with(session, req_ids):
    project = Project(name="Widen", prefix="FLT", status="Active")
    session.add(project)
    await session.flush()
    for req_id in req_ids:
        session.add(
            Requirement(project_id=project.id, req_id=req_id, title=f"r {req_id}", status="Draft")
        )
    await session.flush()
    return project


@pytest.mark.asyncio
async def test_crossing_999_widens_the_ids_already_stored(session):
    project = await _project_with(session, ["FLT-REQ-001", "FLT-REQ-042", "FLT-REQ-999"])

    new_id = await next_doc_id(session, Requirement, Requirement.req_id, project.id, "FLT", "REQ")

    assert new_id == "FLT-REQ-1000"

    stored = sorted(
        (
            await session.execute(
                select(Requirement.req_id).where(Requirement.project_id == project.id)
            )
        )
        .scalars()
        .all()
    )
    assert stored == ["FLT-REQ-0001", "FLT-REQ-0042", "FLT-REQ-0999"]
    # One width across the project, so plain string ordering is still correct.
    assert len({s.rsplit("-", 1)[1].__len__() for s in stored}) == 1


@pytest.mark.asyncio
async def test_below_the_boundary_nothing_is_rewritten(session):
    project = await _project_with(session, ["FLT-REQ-001", "FLT-REQ-002"])

    new_id = await next_doc_id(session, Requirement, Requirement.req_id, project.id, "FLT", "REQ")

    assert new_id == "FLT-REQ-003"
    stored = sorted(
        (
            await session.execute(
                select(Requirement.req_id).where(Requirement.project_id == project.id)
            )
        )
        .scalars()
        .all()
    )
    assert stored == ["FLT-REQ-001", "FLT-REQ-002"]


@pytest.mark.asyncio
async def test_widening_does_not_touch_another_type_in_the_same_project(session):
    project = await _project_with(session, ["FLT-REQ-999"])
    from app.models.models import TestCase

    session.add(TestCase(project_id=project.id, tc_id="FLT-TC-001", title="t", status="Draft"))
    await session.flush()

    await next_doc_id(session, Requirement, Requirement.req_id, project.id, "FLT", "REQ")

    tc_ids = (await session.execute(select(TestCase.tc_id))).scalars().all()
    assert tc_ids == ["FLT-TC-001"]
