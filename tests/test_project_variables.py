import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.api import project_variables as project_variables_api
from app.schemas import ProjectVariableUpdate


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_update_project_variable_updates_kind_key_value_and_description():
    item = SimpleNamespace(
        id=42,
        project_id=7,
        kind="variable",
        key="API_URL",
        value="https://old.example.com",
        description="old description",
    )
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_ScalarResult(item), _ScalarResult(None)]),
        flush=AsyncMock(),
        refresh=AsyncMock(),
    )

    response = await project_variables_api.update_project_variable(
        item_id=item.id,
        data=ProjectVariableUpdate(
            kind="parameter",
            key="API_BASE_URL",
            value="https://new.example.com",
            description=None,
        ),
        db=db,
        _current_user=SimpleNamespace(),
    )

    assert response is item
    assert item.kind == "parameter"
    assert item.key == "API_BASE_URL"
    assert item.value == "https://new.example.com"
    assert item.description is None
    db.flush.assert_awaited_once()
    db.refresh.assert_awaited_once_with(item)


@pytest.mark.asyncio
async def test_update_project_variable_rejects_duplicate_kind_key_combination():
    item = SimpleNamespace(
        id=42,
        project_id=7,
        kind="variable",
        key="API_URL",
        value="https://old.example.com",
        description="old description",
    )
    duplicate = SimpleNamespace(id=43, project_id=7, kind="parameter", key="API_BASE_URL")
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_ScalarResult(item), _ScalarResult(duplicate)]),
        flush=AsyncMock(),
        refresh=AsyncMock(),
    )

    with pytest.raises(HTTPException) as exc:
        await project_variables_api.update_project_variable(
            item_id=item.id,
            data=ProjectVariableUpdate(kind="parameter", key="API_BASE_URL"),
            db=db,
            _current_user=SimpleNamespace(),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Variable key already exists in this project"
    db.flush.assert_not_awaited()
    db.refresh.assert_not_awaited()