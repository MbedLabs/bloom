"""Shared FastAPI dependencies."""

import os

from slowapi import Limiter
from starlette.requests import Request

from app.core.observability import client_address

_rate_limit_disabled = os.environ.get("BLOOM_DISABLE_RATE_LIMIT", "").lower() in {
    "1",
    "true",
    "yes",
}


def rate_limit_key(request: Request) -> str:
    """The rate limit key of a request: its client address as client_address() resolves it,
    or 127.0.0.1 when the request has none."""
    return client_address(request.scope) or "127.0.0.1"


limiter = Limiter(
    key_func=rate_limit_key,
    enabled=not _rate_limit_disabled,
    config_filename=os.devnull if os.environ.get("BLOOM_DOTENV_DISABLED") == "1" else None,
)
