"""Pytest local plugins for bloom-app-backend."""

from __future__ import annotations

import os
from pathlib import Path

# Workspace `.env` lives at `budProject/.env` (parent of `bloom-app-backend/`).


def _load_workspace_dotenv_into_environ() -> None:
    """Parse monorepo `.env` into ``os.environ`` for keys not already set (no ``python-dotenv`` dep)."""
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key and key not in os.environ:
            os.environ[key] = val


if os.environ.get("BLOOM_DOTENV_DISABLED") == "1":
    # CI / explicit pytest: shell env wins; strip bloom-prefixed DB so ``DATABASE_URL`` alone applies.
    os.environ.pop("BLOOM_DATABASE_URL", None)
else:
    _load_workspace_dotenv_into_environ()
    if "SECRET_KEY" not in os.environ and os.environ.get("BLOOM_SECRET_KEY"):
        os.environ["SECRET_KEY"] = os.environ["BLOOM_SECRET_KEY"]
