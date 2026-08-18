from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.security import get_external_doc_types
from app.models.user import UserRole


@pytest.mark.asyncio
async def test_get_external_doc_types_allows_admin_without_query():
    db = AsyncMock()
    admin = SimpleNamespace(id=1, role=UserRole.admin)

    allowed = await get_external_doc_types(db, admin, 42)

    assert allowed is None
    db.execute.assert_not_awaited()
