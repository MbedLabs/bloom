from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.security import AccessTerm, require_project_access
from app.models.user import UserRole


def _db_with_membership(membership):
    db = AsyncMock()
    result = SimpleNamespace(
        scalar_one_or_none=lambda: membership,
        scalars=lambda: SimpleNamespace(all=lambda: []),
    )
    db.execute.return_value = result
    return db


@pytest.mark.asyncio
async def test_require_project_access_allows_admin_without_membership():
    db = AsyncMock()
    db.get.return_value = object()
    admin = SimpleNamespace(id=1, role=UserRole.admin)

    membership = await require_project_access(db, admin, 42)

    assert membership is None
    db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_require_project_access_rejects_unassigned_non_admin():
    db = _db_with_membership(None)
    maintainer = SimpleNamespace(id=7, role=UserRole.maintainer)

    with pytest.raises(HTTPException, match="not assigned"):
        await require_project_access(db, maintainer, 42)


@pytest.mark.asyncio
async def test_require_project_access_rejects_a_missing_action():
    user = SimpleNamespace(
        id=7,
        role=UserRole.maintainer,
        access_map={42: (AccessTerm({"REQ": {"view"}}, None, None, frozenset(), False),)},
    )
    with pytest.raises(HTTPException, match="Missing permission"):
        await require_project_access(AsyncMock(), user, 42, permission=("edit", "REQ"))


@pytest.mark.asyncio
async def test_require_project_access_allows_an_explicit_action():
    user = SimpleNamespace(
        id=7,
        role=UserRole.maintainer,
        access_map={42: (AccessTerm({"REQ": {"view", "edit"}}, None, None, frozenset(), False),)},
    )
    assert await require_project_access(AsyncMock(), user, 42, permission=("edit", "REQ")) is None
