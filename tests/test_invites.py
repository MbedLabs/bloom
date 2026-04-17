from datetime import datetime, timedelta

import pytest

from app.models.user_token import UserToken, UserTokenPurpose
from app.services.token_service import hash_token


def test_token_hash_is_deterministic():
    token = "abc123"
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != hash_token("different")


def test_user_token_purpose_values():
    assert UserTokenPurpose.invite.value == "invite"
    assert UserTokenPurpose.email_verification.value == "email_verification"
    assert UserTokenPurpose.password_reset.value == "password_reset"


def test_user_token_expiry_semantics():
    token = UserToken(
        user_id=1,
        purpose=UserTokenPurpose.invite,
        token_hash="hash",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    assert token.used_at is None
    assert token.expires_at > datetime.utcnow()
