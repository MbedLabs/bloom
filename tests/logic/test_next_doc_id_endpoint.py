"""The create screen's id preview must come from the server, not a guess."""

import pytest

from app.core.id_generator import compute_next_id


def test_preview_matches_allocation_for_an_empty_project():
    assert compute_next_id([], "PRJ", "REQ") == "PRJ-REQ-001"


def test_preview_advances_past_the_taken_id():
    """The reported bug: 001 exists, yet the screen still offered 001."""
    assert compute_next_id(["PRJ-REQ-001"], "PRJ", "REQ") == "PRJ-REQ-002"


def test_preview_uses_max_not_count_so_deletions_do_not_reuse_ids():
    existing = ["PRJ-REQ-001", "PRJ-REQ-007"]

    assert compute_next_id(existing, "PRJ", "REQ") == "PRJ-REQ-008"


def test_preview_ignores_other_types_and_projects():
    existing = ["PRJ-TC-009", "ABC-REQ-005", "PRJ-REQ-002"]

    assert compute_next_id(existing, "PRJ", "REQ") == "PRJ-REQ-003"


def test_preview_rejects_an_unsupported_type_code():
    with pytest.raises(ValueError):
        compute_next_id([], "PRJ", "NOPE")


def test_endpoint_is_registered_outside_the_document_id_route():
    """`next-doc-id` must not be parsed as a document whose id is 'next-doc-id'."""
    from app.api import docs_facade

    paths = [route.path for route in docs_facade.router.routes]

    assert "/projects/{project_ref}/next-doc-id/{type_code}" in paths
