"""Multi-worker-safe ReqIF import rate and concurrency controls."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import ImportAttempt


def _advisory_key(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "big", signed=True)


async def _lock(db: AsyncSession, key: str) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        await db.execute(select(func.pg_advisory_xact_lock(_advisory_key(key))))


async def begin_import_attempt(db: AsyncSession, *, user_id: int, project_id: int) -> ImportAttempt:
    now = datetime.utcnow()
    await _lock(db, f"reqif-user:{user_id}")
    await _lock(db, f"reqif-project:{project_id}")
    await db.execute(
        update(ImportAttempt)
        .where(
            ImportAttempt.status == "active",
            ImportAttempt.expires_at <= now,
        )
        .values(status="expired", completed_at=now)
    )
    window = now - timedelta(minutes=15)
    count = await db.scalar(
        select(func.count(ImportAttempt.id)).where(
            ImportAttempt.user_id == user_id,
            ImportAttempt.created_at >= window,
        )
    )
    if (count or 0) >= settings.REQIF_IMPORTS_PER_15_MINUTES:
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="ReqIF import rate limit exceeded.",
            headers={"Retry-After": "900"},
        )
    active = await db.scalar(
        select(ImportAttempt.id).where(
            ImportAttempt.project_id == project_id,
            ImportAttempt.status == "active",
            ImportAttempt.expires_at > now,
        )
    )
    if active is not None:
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="A ReqIF import is already active for this project.",
            headers={"Retry-After": "60"},
        )
    attempt = ImportAttempt(
        user_id=user_id,
        project_id=project_id,
        status="active",
        created_at=now,
        expires_at=now + timedelta(seconds=settings.REQIF_PROCESSING_TIMEOUT_SECONDS + 60),
    )
    db.add(attempt)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="A ReqIF import is already active for this project.",
            headers={"Retry-After": "60"},
        ) from exc
    await db.refresh(attempt)
    return attempt


async def finish_import_attempt(db: AsyncSession, attempt_id: int, status: str) -> None:
    if status not in {"completed", "failed", "timeout"}:
        raise ValueError("Invalid import-attempt terminal status.")
    await db.execute(
        update(ImportAttempt)
        .where(ImportAttempt.id == attempt_id)
        .values(status=status, completed_at=datetime.utcnow())
    )
    await db.commit()
