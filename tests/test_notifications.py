"""Tests for in-app notifications: service, API, and emission hooks."""

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.notifications import (
    list_notifications,
    mark_all_read,
    mark_read,
    unread_count,
)
from app.api.requirements import create_requirement, update_requirement
from app.core.database import Base
from app.models import Notification, Project, Requirement
from app.models.user import User, UserRole
from app.schemas import RequirementCreate, RequirementUpdate
from app.services.notification_service import notify, notify_assignment


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        db.add(Project(name="Alpha", prefix="ALP"))
        db.add_all(
            [
                User(
                    email="admin@test.local",
                    full_name="Ada Admin",
                    hashed_password="x",
                    role=UserRole.admin,
                ),
                User(
                    email="rev@test.local",
                    full_name="Rita Reviewer",
                    hashed_password="x",
                    role=UserRole.maintainer,
                ),
            ]
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _users(db):
    admin = (await db.execute(select(User).where(User.email == "admin@test.local"))).scalar_one()
    reviewer = (await db.execute(select(User).where(User.email == "rev@test.local"))).scalar_one()
    return admin, reviewer


async def test_notify_creates_row_and_skips_self(session):
    admin, reviewer = await _users(session)

    created = await notify(
        session, user_id=reviewer.id, event_type="test", title="Hello", actor=admin
    )
    assert created is not None

    skipped = await notify(session, user_id=admin.id, event_type="test", title="Self", actor=admin)
    assert skipped is None

    rows = (await session.execute(select(Notification))).scalars().all()
    assert len(rows) == 1
    assert rows[0].user_id == reviewer.id


async def test_notify_assignment_only_fires_on_change(session):
    admin, reviewer = await _users(session)
    await notify_assignment(
        session,
        assignee_id=reviewer.id,
        previous_assignee_id=reviewer.id,  # unchanged
        role_label="reviewer",
        artefact_label="requirement ALP-REQ-001",
        project_id=1,
        link_path="/x",
        actor=admin,
    )
    assert (await session.execute(select(Notification))).scalars().all() == []


async def test_requirement_create_notifies_reviewer(session):
    admin, reviewer = await _users(session)
    await create_requirement(
        data=RequirementCreate(project_id=1, title="Login shall work", reviewer_id=reviewer.id),
        db=session,
        current_user=admin,
    )
    rows = (await session.execute(select(Notification))).scalars().all()
    assert len(rows) == 1
    n = rows[0]
    assert n.user_id == reviewer.id
    assert n.event_type == "assignment"
    assert "reviewer" in n.title
    assert n.link_path and "/docs/requirements/ALP-REQ-001" in n.link_path


async def test_requirement_update_notifies_new_approver_once(session):
    admin, reviewer = await _users(session)
    await create_requirement(
        data=RequirementCreate(project_id=1, title="Base req"),
        db=session,
        current_user=admin,
    )
    req = (await session.execute(select(Requirement))).scalars().one()

    await update_requirement(
        requirement_id=req.id,
        data=RequirementUpdate(approver_id=reviewer.id),
        db=session,
        current_user=admin,
    )
    rows = (await session.execute(select(Notification))).scalars().all()
    assert len(rows) == 1
    assert rows[0].event_type == "assignment"
    assert "approver" in rows[0].title

    # unchanged approver on a second update -> no duplicate
    await update_requirement(
        requirement_id=req.id,
        data=RequirementUpdate(approver_id=reviewer.id, title="Renamed"),
        db=session,
        current_user=admin,
    )
    rows = (await session.execute(select(Notification))).scalars().all()
    assert len(rows) == 1


async def test_list_unread_and_mark_read_flow(session):
    admin, reviewer = await _users(session)
    for i in range(3):
        await notify(session, user_id=reviewer.id, event_type="test", title=f"N{i}", actor=admin)

    listed = await list_notifications(
        unread_only=False, limit=20, offset=0, db=session, current_user=reviewer
    )
    assert listed.total == 3 and listed.unread == 3

    count = await unread_count(db=session, current_user=reviewer)
    assert count.unread == 3

    first = listed.items[0]
    marked = await mark_read(notification_id=first.id, db=session, current_user=reviewer)
    assert marked.read_at is not None
    assert (await unread_count(db=session, current_user=reviewer)).unread == 2

    await mark_all_read(db=session, current_user=reviewer)
    assert (await unread_count(db=session, current_user=reviewer)).unread == 0

    unread_list = await list_notifications(
        unread_only=True, limit=20, offset=0, db=session, current_user=reviewer
    )
    assert unread_list.items == [] and unread_list.total == 0


async def test_users_cannot_read_each_others_notifications(session):
    admin, reviewer = await _users(session)
    created = await notify(
        session, user_id=reviewer.id, event_type="test", title="Private", actor=admin
    )

    listed = await list_notifications(
        unread_only=False, limit=20, offset=0, db=session, current_user=admin
    )
    assert listed.total == 0

    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await mark_read(notification_id=created.id, db=session, current_user=admin)
    assert exc.value.status_code == 404
