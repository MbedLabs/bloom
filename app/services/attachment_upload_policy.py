"""Multi-worker-safe rate and concurrency controls for human attachment uploads."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AttachmentUploadAttempt, AttachmentUploadLease


def _advisory_key(value: str) -> int:
    raw = hashlib.sha256(value.encode("utf-8")).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


async def _lock_user(db: AsyncSession, user_id: int) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        await db.execute(
            select(func.pg_advisory_xact_lock(_advisory_key(f"attachment-user:{user_id}")))
        )


async def reserve_attachment_upload(db: AsyncSession, *, user_id: int) -> AttachmentUploadLease:
    """Record an upload start and reserve the user's only active upload slot."""

    now = datetime.utcnow()
    window_start = now - timedelta(minutes=15)
    await _lock_user(db, user_id)
    await db.execute(delete(AttachmentUploadLease).where(AttachmentUploadLease.expires_at <= now))
    await db.execute(
        delete(AttachmentUploadAttempt).where(AttachmentUploadAttempt.created_at < window_start)
    )

    attempts = await db.scalar(
        select(func.count(AttachmentUploadAttempt.id)).where(
            AttachmentUploadAttempt.user_id == user_id,
            AttachmentUploadAttempt.created_at >= window_start,
        )
    )
    if (attempts or 0) >= settings.ATTACHMENT_UPLOADS_PER_15_MINUTES:
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="Attachment upload rate limit exceeded; retry after the 15-minute window.",
            headers={"Retry-After": "900"},
        )

    active = await db.scalar(
        select(AttachmentUploadLease.id).where(
            AttachmentUploadLease.user_id == user_id,
            AttachmentUploadLease.expires_at > now,
        )
    )
    if active is not None:
        db.add(AttachmentUploadAttempt(user_id=user_id, created_at=now))
        await db.commit()
        raise HTTPException(
            status_code=429,
            detail="An attachment upload is already active for this user.",
            headers={"Retry-After": "60"},
        )

    lease = AttachmentUploadLease(
        id=str(uuid.uuid4()),
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    db.add(AttachmentUploadAttempt(user_id=user_id, created_at=now))
    db.add(lease)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=429,
            detail="An attachment upload is already active for this user.",
            headers={"Retry-After": "60"},
        ) from exc
    await db.refresh(lease)
    return lease


async def release_attachment_upload(db: AsyncSession, lease_id: str) -> None:
    """Release a reservation after the endpoint has settled its own transaction."""

    await db.execute(delete(AttachmentUploadLease).where(AttachmentUploadLease.id == lease_id))
    await db.commit()
