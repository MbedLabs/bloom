"""
First-run setup flow.

The endpoints are unauthenticated, so the tests that matter are the ones
proving the window closes: once any user exists, the instance must refuse to
create another administrator and must stop advertising that setup is needed.

Unlike the rest of the HTTP suite this builds its own throwaway SQLite engine
rather than using ``api_client``. The shared session-scoped client runs against
a real Postgres that already holds users, and the state under test here is an
instance that has none — which cannot be reached without destroying that
database.
"""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole

VALID_PASSWORD = "a-sufficiently-long-passphrase"


def _payload(**overrides):
    body = {
        "email": "owner@example.com",
        "password": VALID_PASSWORD,
        "full_name": "Instance Owner",
    }
    body.update(overrides)
    return body


@pytest_asyncio.fixture
async def empty_engine(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'setup.db'}")
    async with engine.begin() as conn:
        from app import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_maker(empty_engine):
    return async_sessionmaker(empty_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def fresh_client(session_maker):
    """A client whose instance has never had a user.

    The app object is not started through its lifespan here, so nothing seeds an
    administrator: this is the empty-table state a packaged first boot begins
    from.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app, base_url="http://test")
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_status_reports_setup_required_on_empty_instance(fresh_client):
    response = fresh_client.get("/api/setup/status")

    assert response.status_code == 200
    assert response.json() == {"setup_required": True}


@pytest.mark.asyncio
async def test_creates_an_active_admin_then_closes_the_window(fresh_client, session_maker):
    created = fresh_client.post("/api/setup", json=_payload())
    assert created.status_code == 201

    async with session_maker() as session:
        result = await session.execute(select(User).where(User.email == "owner@example.com"))
        admin = result.scalar_one()
        assert admin.role is UserRole.admin
        assert admin.is_active is True
        # The password must be hashed, never stored as given.
        assert admin.hashed_password != VALID_PASSWORD

    assert fresh_client.get("/api/setup/status").json() == {"setup_required": False}

    second = fresh_client.post("/api/setup", json=_payload(email="squatter@example.com"))
    assert second.status_code == 409

    async with session_maker() as session:
        total = await session.execute(select(func.count()).select_from(User))
        assert total.scalar_one() == 1


def test_rejects_a_password_below_the_shared_policy(fresh_client):
    response = fresh_client.post("/api/setup", json=_payload(password="short"))

    assert response.status_code == 422
