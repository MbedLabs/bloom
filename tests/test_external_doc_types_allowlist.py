from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.security import get_external_doc_types
from app.models.user import UserRole


def _scalar_result(values):
    return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: values))


@pytest.mark.asyncio
async def test_get_external_doc_types_returns_external_allowlist():
    membership = SimpleNamespace(id=11, role="external")
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: membership),
        _scalar_result(["REQ", "TC"]),
    ]
    external = SimpleNamespace(id=7, role=UserRole.external)

    allowed = await get_external_doc_types(db, external, 42)

    assert allowed == {"REQ", "TC"}
