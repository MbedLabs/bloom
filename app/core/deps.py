"""Shared FastAPI dependencies."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_rate_limit_disabled = os.environ.get("BLOOM_DISABLE_RATE_LIMIT", "").lower() in {
    "1",
    "true",
    "yes",
}
limiter = Limiter(
    key_func=get_remote_address,
    enabled=not _rate_limit_disabled,
    config_filename=os.devnull if os.environ.get("BLOOM_DOTENV_DISABLED") == "1" else None,
)
