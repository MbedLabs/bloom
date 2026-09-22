"""Outbound webhook emitter: signing, delivery outcomes, and the notify() wiring."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import settings
from app.services import webhook_emitter


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class _FakeClient:
    calls: list = []
    status = 200

    def __init__(self, *args, **kwargs):
        type(self).init_kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, content=None, headers=None):
        _FakeClient.calls.append({"url": url, "content": content, "headers": headers})
        return _FakeResponse(_FakeClient.status)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.status = 200
    monkeypatch.setattr(settings, "OUTBOUND_WEBHOOK_URL", "")
    monkeypatch.setattr(settings, "OUTBOUND_WEBHOOK_SECRET", "")
    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    yield


@pytest.mark.asyncio
async def test_disabled_is_a_noop():
    assert await webhook_emitter.emit("requirement.approved", project_id=1) is False
    assert _FakeClient.calls == []


@pytest.mark.asyncio
async def test_posts_signed_payload(monkeypatch):
    monkeypatch.setattr(settings, "OUTBOUND_WEBHOOK_URL", "http://hook.test/in")
    monkeypatch.setattr(settings, "OUTBOUND_WEBHOOK_SECRET", "s3cr3t")

    ok = await webhook_emitter.emit(
        "requirement.approved", project_id=7, title="R-1 approved", recipient_user_id=3
    )

    assert ok is True
    assert len(_FakeClient.calls) == 1
    call = _FakeClient.calls[0]
    assert call["url"] == "http://hook.test/in"
    assert call["headers"]["X-Bloom-Event"] == "requirement.approved"
    assert call["headers"]["Content-Type"] == "application/json"
    payload = json.loads(call["content"])
    assert payload["event"] == "requirement.approved"
    assert payload["project_id"] == 7
    assert payload["recipient_user_id"] == 3
    expected = "sha256=" + hmac.new(b"s3cr3t", call["content"], hashlib.sha256).hexdigest()
    assert call["headers"]["X-Bloom-Signature"] == expected


@pytest.mark.asyncio
async def test_unsigned_when_no_secret(monkeypatch):
    monkeypatch.setattr(settings, "OUTBOUND_WEBHOOK_URL", "http://hook.test/in")
    await webhook_emitter.emit("x")
    assert "X-Bloom-Signature" not in _FakeClient.calls[0]["headers"]


@pytest.mark.asyncio
async def test_non_2xx_returns_false(monkeypatch):
    monkeypatch.setattr(settings, "OUTBOUND_WEBHOOK_URL", "http://hook.test/in")
    _FakeClient.status = 502
    assert await webhook_emitter.emit("x") is False


@pytest.mark.asyncio
async def test_transport_error_is_swallowed(monkeypatch):
    monkeypatch.setattr(settings, "OUTBOUND_WEBHOOK_URL", "http://hook.test/in")

    class _Boom(_FakeClient):
        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "AsyncClient", _Boom)
    assert await webhook_emitter.emit("x") is False


@pytest.mark.asyncio
async def test_notify_emits_the_event(monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app.services import notification_service

    emit = AsyncMock(return_value=True)
    monkeypatch.setattr(webhook_emitter, "emit", emit)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        note = await notification_service.notify(
            db,
            user_id=5,
            event_type="requirement.approved",
            title="R-1",
            project_id=2,
            link_path="/requirements/1",
        )
    await engine.dispose()

    assert note is not None
    emit.assert_awaited_once()
    assert emit.await_args.args[0] == "requirement.approved"
    assert emit.await_args.kwargs["project_id"] == 2
    assert emit.await_args.kwargs["recipient_user_id"] == 5
