"""Least-privilege Bud-to-Bloom service credential tests."""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.core.security import create_access_token, get_current_user
from app.core.service_auth import (
    create_service_credential,
    require_bud_sync_token,
    revoke_service_credential,
)
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def credential_db(monkeypatch):
    monkeypatch.setattr(settings, "SERVICE_TOKEN_PEPPER", "p" * 32)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        admin = User(
            email="admin-service@example.com",
            full_name="Admin",
            hashed_password="hash",
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        yield db, admin
    await engine.dispose()


@pytest.mark.asyncio
async def test_service_token_is_hashed_scoped_and_returned_only_at_creation(
    credential_db,
):
    db, admin = credential_db
    credential, raw = await create_service_credential(db, created_by_user_id=admin.id, name="Bud")

    assert raw.startswith("blm_sync_")
    assert credential.scope == "test-results:write"
    assert credential.token_hash != raw
    assert raw not in credential.token_hash
    assert credential.expires_at <= datetime.utcnow() + timedelta(days=90, seconds=5)
    authenticated = await require_bud_sync_token(token=raw, db=db)
    assert authenticated.id == credential.id


@pytest.mark.asyncio
async def test_service_token_is_not_a_user_or_admin_jwt(credential_db):
    db, admin = credential_db
    _, raw = await create_service_credential(db, created_by_user_id=admin.id, name="Bud")

    with pytest.raises(HTTPException) as error:
        await get_current_user(token=raw, db=db)

    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_user_jwt_must_carry_an_explicit_user_type(credential_db):
    db, admin = credential_db
    ambiguous = create_access_token({"sub": str(admin.id)})

    with pytest.raises(HTTPException) as error:
        await get_current_user(token=ambiguous, db=db)

    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_revoked_and_expired_service_tokens_are_rejected(credential_db):
    db, admin = credential_db
    credential, raw = await create_service_credential(db, created_by_user_id=admin.id, name="Bud")
    credential_id = credential.id
    await revoke_service_credential(db, credential_id)

    with pytest.raises(HTTPException) as revoked:
        await require_bud_sync_token(token=raw, db=db)
    assert revoked.value.status_code == 401

    expired, expired_raw = await create_service_credential(
        db, created_by_user_id=admin.id, name="Expired"
    )
    expired.expires_at = datetime.utcnow() - timedelta(seconds=1)
    await db.commit()
    with pytest.raises(HTTPException) as past_deadline:
        await require_bud_sync_token(token=expired_raw, db=db)
    assert past_deadline.value.status_code == 401
