from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.security import require_external_doc_type_access
from app.models.user import UserRole


def _scalar_result(values):
    return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: values))


@pytest.mark.asyncio
async def test_require_external_doc_type_access_allows_granted_type():
    membership = SimpleNamespace(id=11, role="external")
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: membership),
        _scalar_result(["REQ"]),
    ]
    external = SimpleNamespace(id=7, role=UserRole.external)

    await require_external_doc_type_access(db, external, 42, "REQ")
