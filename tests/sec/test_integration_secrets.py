"""External tracker credentials and webhook secrets are encrypted at rest."""

import asyncio

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import IntegrationSetting, Project, User
from app.models.user import UserRole
from app.services.integration_secrets import (
    ENVELOPE_PREFIX,
    decrypt_integration_secret,
    encrypt_integration_secret,
    is_encrypted,
)

# ---------------------------------------------------------------------------
# Crypto module: correctly encrypted values are usable; wrong/missing keys fail
# closed; legacy plaintext is rejected.
# ---------------------------------------------------------------------------


def test_round_trip_hides_plaintext():
    envelope = encrypt_integration_secret("ghp_super_secret_token")
    assert envelope.startswith(ENVELOPE_PREFIX)
    assert "ghp_super_secret_token" not in envelope
    assert decrypt_integration_secret(envelope) == "ghp_super_secret_token"


def test_rotation_yields_a_new_ciphertext():
    first = encrypt_integration_secret("same-secret")
    second = encrypt_integration_secret("same-secret")
    assert first != second  # Fernet IV/timestamp differ; a rotation replaces the value
    assert decrypt_integration_secret(first) == decrypt_integration_secret(second) == "same-secret"


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "INTEGRATION_ENCRYPTION_KEY", "")
    with pytest.raises(HTTPException) as exc:
        encrypt_integration_secret("x")
    assert exc.value.status_code == 503


def test_malformed_key_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "INTEGRATION_ENCRYPTION_KEY", "not-a-valid-fernet-key")
    with pytest.raises(HTTPException) as exc:
        encrypt_integration_secret("x")
    assert exc.value.status_code == 503


def test_wrong_key_cannot_decrypt(monkeypatch):
    envelope = encrypt_integration_secret("secret")  # encrypted with the conftest key
    monkeypatch.setattr(settings, "INTEGRATION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(HTTPException) as exc:
        decrypt_integration_secret(envelope)
    assert exc.value.status_code == 503


def test_legacy_plaintext_is_rejected():
    with pytest.raises(HTTPException) as exc:
        decrypt_integration_secret("plaintext-not-enveloped")
    assert exc.value.status_code == 503


def test_is_encrypted():
    assert is_encrypted(encrypt_integration_secret("x"))
    assert not is_encrypted("plaintext")
    assert not is_encrypted(None)


# ---------------------------------------------------------------------------
# API path: the create/update endpoints store only ciphertext (raw secrets never
# reach the database), and rotation replaces the stored envelope.
# ---------------------------------------------------------------------------


def _build_harness():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    actor = {"id": None}

    async def _create_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_get_current_user() -> User:
        async with session_maker() as session:
            return await session.get(User, actor["id"])

    asyncio.run(_create_schema())
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    return TestClient(app, base_url="http://test"), session_maker, actor, engine


def _seed_admin_and_project(session_maker):
    async def _seed():
        async with session_maker() as session:
            admin = User(
                email="crypto-admin@example.com",
                full_name="Crypto Admin",
                hashed_password=get_password_hash("unused-admin-password"),
                role=UserRole.admin,
                is_active=True,
            )
            project = Project(name="Crypto Project", prefix="CRY")
            session.add_all([admin, project])
            await session.commit()
            await session.refresh(admin)
            await session.refresh(project)
            return admin.id, project.id

    return asyncio.run(_seed())


def _stored_secrets(session_maker, project_id):
    async def _read():
        async with session_maker() as session:
            row = (
                await session.execute(
                    select(IntegrationSetting).where(IntegrationSetting.project_id == project_id)
                )
            ).scalar_one()
            return row.token_encrypted, row.webhook_secret

    return asyncio.run(_read())


def test_created_credentials_are_encrypted_at_rest_and_rotate():
    client, session_maker, actor, engine = _build_harness()
    raw_token = "ghp_raw_access_token_value"
    raw_secret = "raw-webhook-signing-secret"
    try:
        admin_id, project_id = _seed_admin_and_project(session_maker)
        actor["id"] = admin_id

        resp = client.post(
            "/api/integrations/settings",
            json={
                "project_id": project_id,
                "tracker": "github",
                "token": raw_token,
                "webhook_secret": raw_secret,
                "enabled": True,
            },
        )
        assert resp.status_code == 201, resp.text
        # The response never echoes the raw secrets.
        body = resp.json()
        assert body["has_token"] is True and body["has_webhook_secret"] is True
        assert raw_token not in resp.text and raw_secret not in resp.text

        stored_token, stored_secret = _stored_secrets(session_maker, project_id)
        # Raw values never reach the database; both are Fernet envelopes.
        assert stored_token != raw_token and is_encrypted(stored_token)
        assert stored_secret != raw_secret and is_encrypted(stored_secret)
        assert decrypt_integration_secret(stored_token) == raw_token
        assert decrypt_integration_secret(stored_secret) == raw_secret

        # Rotation: a new token replaces the stored envelope.
        setting_id = body["id"]
        rotate = client.patch(
            f"/api/integrations/settings/{setting_id}",
            json={"token": "ghp_rotated_token"},
        )
        assert rotate.status_code == 200, rotate.text
        rotated_token, _ = _stored_secrets(session_maker, project_id)
        assert rotated_token != stored_token
        assert decrypt_integration_secret(rotated_token) == "ghp_rotated_token"
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
