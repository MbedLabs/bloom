"""Orphan reconciliation for Bloom's attachment volume."""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentAttachment
from app.services import object_store
from app.services.attachment_storage import get_attachment_root


@dataclass(frozen=True)
class CleanupReport:
    orphan_files: int = 0
    missing_files: int = 0
    leader_acquired: bool = True


def _safe_attachment_root() -> Path:
    root = get_attachment_root().resolve()
    if root == Path(root.anchor) or root == Path.home().resolve():
        raise RuntimeError("Refusing attachment cleanup for an unsafe storage root.")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _direct_child(root: Path, storage_path: str) -> Path | None:
    path = (root / storage_path).resolve()
    return path if path.parent == root else None


async def reconcile_attachments(
    db: AsyncSession, *, orphan_grace_seconds: int = 3600
) -> CleanupReport:
    """Delete old files with no attachment row and report missing referenced files.

    With S3 storage the bucket is reconciled (a file is missing when the bucket lacks
    it), and the local mirror, when kept, is cleared of orphans too.
    """

    root = _safe_attachment_root() if object_store.keeps_local_copy() else None
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        acquired = await db.scalar(select(func.pg_try_advisory_xact_lock(1730554203)))
        if not acquired:
            await db.rollback()
            return CleanupReport(leader_acquired=False)

    referenced = set((await db.scalars(select(DocumentAttachment.storage_path))).all())
    orphan_cutoff = time.time() - orphan_grace_seconds
    orphan_count = 0
    if root is not None:
        for path in root.iterdir():
            try:
                is_old_orphan = (
                    path.is_file()
                    and path.name not in referenced
                    and path.stat().st_mtime < orphan_cutoff
                )
            except OSError:
                continue
            if is_old_orphan:
                with contextlib.suppress(OSError):
                    path.unlink()
                    orphan_count += 1

    if object_store.s3_enabled():
        cutoff = datetime.fromtimestamp(orphan_cutoff, tz=timezone.utc)
        present = set()
        for stored in await object_store.list_objects():
            present.add(stored.name)
            if stored.name not in referenced and stored.last_modified < cutoff:
                await object_store.delete(stored.name)
                orphan_count += 1
        missing_count = len(referenced - present)
    else:
        missing_count = 0
        for storage_path in referenced:
            path = _direct_child(root, storage_path)
            if path is None or not path.is_file():
                missing_count += 1

    await db.commit()
    return CleanupReport(orphan_files=orphan_count, missing_files=missing_count)
