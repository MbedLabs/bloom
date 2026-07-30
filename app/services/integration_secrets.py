"""Authenticated encryption for external tracker credentials and webhook secrets.

GitHub/GitLab access tokens and webhook secrets are encrypted with Fernet
(AES-128-CBC + HMAC) before they are stored, in a versioned envelope
``fernet:v1:<ciphertext>``. They are decrypted only immediately before an
outbound tracker request or webhook-signature verification, and never returned
in API responses, exceptions, or logs. Every path fails closed when the key is
missing, malformed, or a stored value cannot be decrypted.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.core.config import settings

ENVELOPE_PREFIX = "fernet:v1:"


def _fernet() -> Fernet:
    if not settings.INTEGRATION_ENCRYPTION_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "BLOOM_INTEGRATION_ENCRYPTION_KEY must be configured before "
                "storing or using integration credentials."
            ),
        )
    try:
        return Fernet(settings.INTEGRATION_ENCRYPTION_KEY.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="BLOOM_INTEGRATION_ENCRYPTION_KEY must be a valid Fernet key.",
        ) from exc


def is_encrypted(value: str | None) -> bool:
    """True if ``value`` is a stored envelope (vs. legacy plaintext / None)."""
    return bool(value) and value.startswith(ENVELOPE_PREFIX)


def encrypt_integration_secret(secret: str) -> str:
    """Encrypt a credential into a ``fernet:v1:`` envelope."""
    encrypted = _fernet().encrypt(secret.encode("utf-8")).decode("ascii")
    return ENVELOPE_PREFIX + encrypted


def decrypt_integration_secret(envelope: str) -> str:
    """Decrypt a stored envelope. Fails closed on legacy plaintext or any key /
    ciphertext problem — the caller must rotate the credential."""
    if not envelope.startswith(ENVELOPE_PREFIX):
        raise HTTPException(
            status_code=503,
            detail=(
                "Integration credential is stored in an unsupported format; "
                "rotate it (re-enter the token/secret)."
            ),
        )
    try:
        plaintext = _fernet().decrypt(envelope[len(ENVELOPE_PREFIX) :].encode("ascii"))
    except (InvalidToken, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Integration credential could not be decrypted; rotate it.",
        ) from exc
    return plaintext.decode("utf-8")
