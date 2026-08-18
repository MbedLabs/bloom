"""Attachment-volume reconciliation tests."""

from __future__ import annotations

import asyncio
import os
import time
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import attachment_storage
from app.services.attachment_cleanup import reconcile_attachments


class _Scalars:
    def __init__(self, values: list[str]):
        self._values = values

    def all(self) -> list[str]:
        return self._values


class _Dialect:
    name = "sqlite"


class _Bind:
    dialect = _Dialect()


class _Session:
    bind = _Bind()

    def __init__(self, referenced: list[str]):
        self.referenced = referenced
        self.committed = False

    async def scalars(self, _statement):
        return _Scalars(self.referenced)

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_reconcile_removes_only_old_unreferenced_attachment_files(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ATTACHMENT_DIR", str(tmp_path))
    monkeypatch.setattr(attachment_storage, "_ROOT", None)

    referenced = tmp_path / "referenced.txt"
    referenced.write_bytes(b"kept")
    fresh_orphan = tmp_path / "fresh.txt"
    fresh_orphan.write_bytes(b"in-flight")
    old_orphan = tmp_path / "old.txt"
    old_orphan.write_bytes(b"leaked")
    old_timestamp = time.time() - (2 * 60 * 60)
    os.utime(old_orphan, (old_timestamp, old_timestamp))
    session = _Session(["referenced.txt", "missing.txt"])

    report = await reconcile_attachments(session, orphan_grace_seconds=3600)

    assert report.orphan_files == 1
    assert report.missing_files == 1
    assert referenced.exists()
    assert fresh_orphan.exists()
    assert not old_orphan.exists()
    assert session.committed


@pytest.mark.asyncio
async def test_lifespan_starts_attachment_reconciliation(monkeypatch):
    from app import main as main_module

    calls: list[object] = []
    session = object()

    class _SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *_args):
            return None

    async def fake_reconcile(received):
        calls.append(received)
        return SimpleNamespace(leader_acquired=True, orphan_files=0, missing_files=0)

    monkeypatch.setattr(main_module.settings, "RUN_STARTUP_DATA_REPAIR", False)
    monkeypatch.setattr(main_module.settings, "AUTO_SEED_ADMIN", False)
    monkeypatch.setattr(main_module, "async_session_maker", _SessionContext)
    monkeypatch.setattr(
        main_module,
        "reconcile_attachments",
        fake_reconcile,
        raising=False,
    )

    async with main_module.lifespan(main_module.app):
        await asyncio.sleep(0)

    assert calls == [session]
