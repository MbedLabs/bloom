"""Access tokens: a standard HS256 token signs in; an expired one or one with another
algorithm does not."""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.core.security import create_access_token, get_current_user
from app.models.user import User, UserRole


def _part(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _signed(header: dict, payload: dict) -> str:
    signing_input = f"{_part(header)}.{_part(payload)}"
    hashes = {"HS256": hashlib.sha256, "HS512": hashlib.sha512}
    if header["alg"] not in hashes:
        return f"{signing_input}."
    digest = hmac.new(settings.SECRET_KEY.encode(), signing_input.encode(), hashes[header["alg"]])
    signature = base64.urlsafe_b64encode(digest.digest()).rstrip(b"=").decode()
    return f"{signing_input}.{signature}"


def _claims(user: User, minutes: int) -> dict:
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return {
        "sub": str(user.id),
        "type": "user",
        "ver": user.session_version,
        "exp": int(expires.timestamp()),
    }


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        db.add(
            User(email="t@test.local", full_name="T", hashed_password="x", role=UserRole.maintainer)
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _user(db) -> User:
    return await db.get(User, 1)


async def test_a_standard_hs256_token_signs_in(session):
    user = await _user(session)
    token = _signed({"alg": "HS256", "typ": "JWT"}, _claims(user, 5))
    assert (await get_current_user(token=token, db=session)).id == user.id
    issued = create_access_token({"sub": str(user.id), "type": "user", "ver": user.session_version})
    assert (await get_current_user(token=issued, db=session)).id == user.id


@pytest.mark.parametrize(
    "header, minutes",
    [
        ({"alg": "HS256", "typ": "JWT"}, -5),
        ({"alg": "HS512", "typ": "JWT"}, 5),
        ({"alg": "none", "typ": "JWT"}, 5),
    ],
)
async def test_an_expired_token_or_another_algorithm_is_refused(session, header, minutes):
    user = await _user(session)
    token = _signed(header, _claims(user, minutes))
    with pytest.raises(HTTPException) as refused:
        await get_current_user(token=token, db=session)
    assert refused.value.status_code == 401
