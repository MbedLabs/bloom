"""Opaque service-token issuance and authentication."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models import ServiceCredential

SERVICE_SCOPE = "test-results:write"
TOKEN_PREFIX = "blm_sync_"
TOKEN_LOOKUP_LENGTH = 20


def _pepper() -> bytes:
    if len(settings.SERVICE_TOKEN_PEPPER) < 32:
        raise HTTPException(
            status_code=503,
            detail="SERVICE_TOKEN_PEPPER must be configured with at least 32 characters.",
        )
    return settings.SERVICE_TOKEN_PEPPER.encode("utf-8")


def _token_hash(raw_token: str) -> str:
    return hmac.new(_pepper(), raw_token.encode("utf-8"), hashlib.sha256).hexdigest()


async def create_service_credential(
    db: AsyncSession,
    *,
    created_by_user_id: int,
    name: str,
    expires_in_days: int = 90,
) -> tuple[ServiceCredential, str]:
    if not 1 <= expires_in_days <= 90:
        raise HTTPException(status_code=422, detail="Expiry must be between 1 and 90 days.")
    raw_token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    credential = ServiceCredential(
        name=name[:100],
        token_prefix=raw_token[:TOKEN_LOOKUP_LENGTH],
        token_hash=_token_hash(raw_token),
        scope=SERVICE_SCOPE,
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
        created_by_user_id=created_by_user_id,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return credential, raw_token


async def revoke_service_credential(db: AsyncSession, credential_id: int) -> None:
    credential = await db.get(ServiceCredential, credential_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Service credential not found.")
    credential.revoked_at = datetime.utcnow()
    await db.commit()


async def require_bud_sync_token(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> ServiceCredential:
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid service credential.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token.startswith(TOKEN_PREFIX):
        raise unauthorized
    credential = await db.scalar(
        select(ServiceCredential).where(
            ServiceCredential.token_prefix == token[:TOKEN_LOOKUP_LENGTH]
        )
    )
    now = datetime.utcnow()
    if (
        credential is None
        or credential.scope != SERVICE_SCOPE
        or credential.revoked_at is not None
        or credential.expires_at <= now
        or not hmac.compare_digest(credential.token_hash, _token_hash(token))
    ):
        raise unauthorized
    credential.last_used_at = now
    await db.flush()
    return credential
