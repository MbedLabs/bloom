"""Simple in-process TTL cache for hot read endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 60) -> None:
        self._store: dict[str, tuple[datetime, T]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if datetime.now(timezone.utc) - ts < self._ttl:
            return value
        del self._store[key]
        return None

    def set(self, key: str, value: T) -> None:
        self._store[key] = (datetime.now(timezone.utc), value)

    def invalidate_prefix(self, prefix: str) -> None:
        self._store = {k: v for k, v in self._store.items() if not k.startswith(prefix)}


dashboard_stats_cache: TTLCache[dict[str, Any]] = TTLCache(ttl_seconds=3)
traceability_cache: TTLCache[Any] = TTLCache(ttl_seconds=120)
docs_facade_cache: TTLCache[Any] = TTLCache(ttl_seconds=10)
