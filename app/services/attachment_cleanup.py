"""Orphan reconciliation for Bloom's attachment volume."""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentAttachment
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
    """Delete old files with no attachment row and report missing referenced files."""

    root = _safe_attachment_root()
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        acquired = await db.scalar(select(func.pg_try_advisory_xact_lock(1730554203)))
        if not acquired:
            await db.rollback()
            return CleanupReport(leader_acquired=False)

    referenced = set((await db.scalars(select(DocumentAttachment.storage_path))).all())
    orphan_cutoff = time.time() - orphan_grace_seconds
    orphan_count = 0
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

    missing_count = 0
    for storage_path in referenced:
        path = _direct_child(root, storage_path)
        if path is None or not path.is_file():
            missing_count += 1

    await db.commit()
    return CleanupReport(orphan_files=orphan_count, missing_files=missing_count)
