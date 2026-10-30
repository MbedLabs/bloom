"""Concurrent denied requests from one address leave exactly one repeated refusal event
(real PostgreSQL)."""

import asyncio
import os
import secrets

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import AuditEvent

REQUESTS = 30


def _database_url() -> str:
    """The test database URL, or a skip when it is not PostgreSQL."""
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    return url


async def _burst(url: str, address: str) -> tuple[list[int], int, int]:
    """Send the denied requests at once from the address; return their statuses, the denied
    api.request count and the repeated refusal count of the address."""
    engine = create_async_engine(url)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _db
    try:
        transport = httpx.ASGITransport(app=app, client=(address, 4321))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            answers = await asyncio.gather(
                *[
                    client.get("/api/projects", headers={"Authorization": "Bearer forged"})
                    for _ in range(REQUESTS)
                ]
            )
        async with maker() as session:
            denied = await session.scalar(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.action == "api.request",
                    AuditEvent.outcome == "denied",
                    AuditEvent.ip == address,
                )
            )
            detected = await session.scalar(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.action == "security.repeated_refusals",
                    AuditEvent.ip == address,
                )
            )
        return [answer.status_code for answer in answers], denied, detected
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await engine.dispose()


def test_concurrent_refusals_from_one_address_leave_one_event():
    url = _database_url()
    address = f"2001:db8::{secrets.token_hex(2)}:{secrets.token_hex(2)}"

    statuses, denied, detected = asyncio.run(_burst(url, address))

    assert statuses == [401] * REQUESTS
    assert denied == REQUESTS
    assert REQUESTS > settings.AUDIT_REFUSAL_THRESHOLD
    assert detected == 1
