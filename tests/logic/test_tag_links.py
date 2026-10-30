"""Tag synchronization rejects invalid pairs while preserving visibility filtering."""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models import ArtefactLink, Project, Requirement, User, UserRole
from app.services.tag_links import sync_tag_links


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.add_all(
            [
                Project(name="Demo", prefix="PRJ"),
                User(
                    email="tags@example.com",
                    full_name="Tags Admin",
                    hashed_password="x",
                    role=UserRole.admin,
                ),
            ]
        )
        await db.flush()
        db.add_all(
            [
                Requirement(project_id=1, req_id="PRJ-REQ-001", title="Source"),
                Requirement(project_id=1, req_id="PRJ-REQ-002", title="Target"),
            ]
        )
        await db.flush()
        yield db
    await engine.dispose()


def _mention(kind="REQ", identifier=2):
    """Create an artefact tag node."""
    return {
        "type": "mention",
        "attrs": {"id": f"{kind}:{identifier}", "mentionSuggestionChar": "#"},
    }


async def _sync(db, source="REQ", content=None):
    """Synchronize a document body for the fixture administrator."""
    return await sync_tag_links(
        db,
        project_id=1,
        source_type=source,
        source_id=1,
        content_json=content or _mention(),
        user=await db.get(User, 1),
    )


async def test_tag_rule_allows_reference_without_manual_role(session):
    assert await _sync(session) == 1
    await session.flush()
    link = (await session.execute(select(ArtefactLink))).scalar_one()
    assert (link.source_type, link.target_type, link.role) == ("REQ", "REQ", "references")
    assert await _sync(session) == 0


@pytest.mark.parametrize(("source", "target"), [("TC", "REQ"), ("REQ", "UNKNOWN")])
async def test_invalid_tag_pair_fails_loudly(session, source, target):
    content = _mention(target)
    with pytest.raises(HTTPException) as failed:
        await _sync(session, source, content)
    assert failed.value.status_code == 422
    assert source in failed.value.detail
    assert target in failed.value.detail
    assert (await session.execute(select(ArtefactLink))).scalars().all() == []


async def test_hidden_tag_is_excluded_without_error_or_link(session, monkeypatch):
    async def hidden(*args, **kwargs):
        return None, False

    monkeypatch.setattr("app.services.tag_links.link_end", hidden)
    assert await _sync(session) == 0
    assert (await session.execute(select(ArtefactLink))).scalars().all() == []


async def test_self_tag_stays_excluded(session):
    assert await _sync(session, content=_mention(identifier=1)) == 0
