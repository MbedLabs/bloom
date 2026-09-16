import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.api.docs_facade import _count_links
from app.core.document_kinds import (
    document_kind_from_slug,
    normalize_document_kind,
    require_document_kind,
)


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


def test_normalize_document_kind_maps_legacy_values_to_canonical_codes():
    assert normalize_document_kind("DOC") == "SPEC"
    assert normalize_document_kind("Specification") == "SPEC"
    assert normalize_document_kind("Protocol") == "PRT"
    assert normalize_document_kind("Report") == "RPT"
    assert normalize_document_kind("External Standard") == "STD"
    assert normalize_document_kind(None) == "SPEC"


def test_require_document_kind_accepts_canonical_codes_and_rejects_unknown_values():
    assert require_document_kind("SPEC") == "SPEC"
    assert require_document_kind("PRT") == "PRT"

    for invalid_value in ("Protocol", "DOC", "OTHER", None):
        with pytest.raises(HTTPException) as exc:
            require_document_kind(invalid_value)

        assert exc.value.status_code == 422
        assert "Supported shared-document kinds" in exc.value.detail
        assert "not accepted on the public API" in exc.value.detail


def test_document_kind_from_slug_maps_shared_document_routes():
    assert document_kind_from_slug("specifications") == "SPEC"
    assert document_kind_from_slug("protocols") == "PRT"
    assert document_kind_from_slug("reports") == "RPT"
    assert document_kind_from_slug("standards") == "STD"


@pytest.mark.asyncio
async def test_count_links_includes_suspect_counts_from_incoming_and_outgoing_links():
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _RowsResult([(10, 2, 1)]),
                _RowsResult([(10, 3, 2)]),
            ]
        )
    )

    result = await _count_links(db, project_id=7, type_code="SPEC", row_ids=[10])

    assert result == {10: {"incoming": 2, "outgoing": 3, "suspect": 3}}
