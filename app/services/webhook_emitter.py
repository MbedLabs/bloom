"""Outbound webhook: POST notable events to an operator-configured URL.

Disabled unless OUTBOUND_WEBHOOK_URL is set, so a default install pays nothing.
Delivery is best effort: a failure is logged and swallowed, never surfaced to the
request that triggered the event. When a secret is configured each body is signed
with HMAC-SHA256 so the receiver can verify it came from this instance.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(settings.OUTBOUND_WEBHOOK_URL)


def sign(body: bytes) -> Optional[str]:
    """HMAC-SHA256 of the body under the configured secret, or None when unset."""
    secret = settings.OUTBOUND_WEBHOOK_SECRET
    if not secret:
        return None
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def emit(
    event_type: str,
    *,
    project_id: Optional[int] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
    link_path: Optional[str] = None,
    recipient_user_id: Optional[int] = None,
) -> bool:
    """Deliver one event. Returns True when the receiver accepted it (2xx), False
    otherwise, including when the webhook is disabled or the POST fails."""
    if not is_enabled():
        return False

    payload = {
        "event": event_type,
        "project_id": project_id,
        "title": title,
        "body": body,
        "link_path": link_path,
        "recipient_user_id": recipient_user_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Bloom-Event": event_type}
    signature = sign(raw)
    if signature:
        headers["X-Bloom-Signature"] = signature

    try:
        async with httpx.AsyncClient(timeout=settings.OUTBOUND_WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(
                settings.OUTBOUND_WEBHOOK_URL, content=raw, headers=headers
            )
        if response.status_code >= 400:
            logger.warning("Outbound webhook for %s returned %s", event_type, response.status_code)
            return False
        return True
    except Exception:  # best effort: never break the triggering request
        logger.exception("Outbound webhook delivery for %s failed", event_type)
        return False
