from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.security import AccessTerm, require_external_doc_type_access
from app.models.user import UserRole


def _scalar_result(values):
    return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: values))


@pytest.mark.asyncio
async def test_require_external_doc_type_access_rejects_disallowed_type():
    membership = SimpleNamespace(id=11, role="external")
    db = AsyncMock()
    db.execute.side_effect = [
        SimpleNamespace(scalar_one_or_none=lambda: membership),
        _scalar_result(["REQ"]),
    ]
    external = SimpleNamespace(
        id=7,
        role=UserRole.external,
        access_map={
            42: (
                AccessTerm(
                    {"*": {"view"}}, frozenset(["REQ"]), frozenset(["customer"]), frozenset(), True
                ),
            )
        },
    )

    with pytest.raises(HTTPException, match="[Nn]ot authorized"):
        await require_external_doc_type_access(db, external, 42, "TC")
