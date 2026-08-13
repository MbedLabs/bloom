"""Documents can be filtered to the artefacts sharing a relationship with one document.

Clicking a relationship used to be a dead end: the role label was inert, and the
id beside it jumped straight to the other document, so there was no way to see a
relationship in the registry. The registry only had blunt link filters
(linked/unlinked/incoming/outgoing), never "related to *this* document".
"""

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.docs_facade import _related_doc_keys, _resolve_doc_by_public_id
from app.core.database import Base
from app.models import ArtefactLink, Project, Requirement, TestCase


@pytest_asyncio.fixture
async def env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as session:
        project = Project(name="Flight", prefix="FLT")
        session.add(project)
        await session.flush()

        req = Requirement(project_id=project.id, req_id="FLT-REQ-001", title="Anchor")
        other_req = Requirement(project_id=project.id, req_id="FLT-REQ-002", title="Unrelated")
        verifying = TestCase(project_id=project.id, tc_id="FLT-TC-001", title="Verifies anchor")
        covering = TestCase(project_id=project.id, tc_id="FLT-TC-002", title="Covers anchor")
        session.add_all([req, other_req, verifying, covering])
        await session.flush()

        session.add_all(
            [
                # anchor -> TC-001 (outgoing, role "verifies")
                ArtefactLink(
                    project_id=project.id,
                    source_type="REQ",
                    source_id=req.id,
                    target_type="TC",
                    target_id=verifying.id,
                    role="verifies",
                    suspect=False,
                ),
                # TC-002 -> anchor (incoming, role "covers")
                ArtefactLink(
                    project_id=project.id,
                    source_type="TC",
                    source_id=covering.id,
                    target_type="REQ",
                    target_id=req.id,
                    role="covers",
                    suspect=False,
                ),
            ]
        )
        await session.commit()
        ids = {
            "project": project.id,
            "req": req.id,
            "other_req": other_req.id,
            "verifying": verifying.id,
            "covering": covering.id,
        }

    yield maker, ids
    await engine.dispose()


@pytest.mark.asyncio
async def test_resolves_a_human_readable_id_to_its_type_and_row(env):
    maker, ids = env
    async with maker() as session:
        assert await _resolve_doc_by_public_id(session, ids["project"], "FLT-REQ-001") == (
            "REQ",
            ids["req"],
        )


@pytest.mark.asyncio
async def test_unknown_document_id_resolves_to_nothing(env):
    maker, ids = env
    async with maker() as session:
        assert await _resolve_doc_by_public_id(session, ids["project"], "FLT-REQ-999") is None


@pytest.mark.asyncio
async def test_related_keys_cover_both_directions(env):
    maker, ids = env
    async with maker() as session:
        related = await _related_doc_keys(session, ids["project"], ("REQ", ids["req"]), None, None)

    assert related == {("TC", ids["verifying"]), ("TC", ids["covering"])}
    # The unrelated requirement must never appear.
    assert ("REQ", ids["other_req"]) not in related


@pytest.mark.asyncio
async def test_related_keys_can_be_narrowed_to_one_role(env):
    maker, ids = env
    async with maker() as session:
        related = await _related_doc_keys(
            session, ids["project"], ("REQ", ids["req"]), "verifies", None
        )

    assert related == {("TC", ids["verifying"])}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "direction,expected_key",
    [("outgoing", "verifying"), ("incoming", "covering")],
)
async def test_related_keys_can_be_narrowed_to_one_direction(env, direction, expected_key):
    maker, ids = env
    async with maker() as session:
        related = await _related_doc_keys(
            session, ids["project"], ("REQ", ids["req"]), None, direction
        )

    assert related == {("TC", ids[expected_key])}


@pytest.mark.asyncio
async def test_a_document_without_relationships_yields_none(env):
    maker, ids = env
    async with maker() as session:
        related = await _related_doc_keys(
            session, ids["project"], ("REQ", ids["other_req"]), None, None
        )

    assert related == set()


@pytest.mark.asyncio
async def test_relationships_do_not_leak_across_projects(env):
    """A link is scoped to its project, so another project must match nothing."""
    maker, ids = env
    async with maker() as session:
        other_project = Project(name="Ground", prefix="GND")
        session.add(other_project)
        await session.flush()
        related = await _related_doc_keys(
            session, other_project.id, ("REQ", ids["req"]), None, None
        )

    assert related == set()


def test_docs_list_exposes_the_relationship_query_parameters():
    import inspect

    from app.api.docs_facade import list_all_docs

    params = inspect.signature(list_all_docs).parameters

    assert "related_to" in params
    assert "role" in params
    assert "direction" in params


@pytest.mark.asyncio
async def test_link_rows_are_scoped_by_project(env):
    """Guards the WHERE clause the filter relies on."""
    maker, ids = env
    async with maker() as session:
        count = await session.scalar(
            sa.select(sa.func.count(ArtefactLink.id)).where(
                ArtefactLink.project_id == ids["project"]
            )
        )

    assert count == 2
