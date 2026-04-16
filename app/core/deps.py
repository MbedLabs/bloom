"""
Shared FastAPI dependencies.

H2: Rate limiting via slowapi.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# ── Rate limiter (H2) ──────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
