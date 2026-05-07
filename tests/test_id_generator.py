"""
Tests for the shared ID generator utility.
Tests the pure compute_next_id function directly -- no DB mocking needed.
"""

import pytest

from app.core.id_generator import compute_next_id, normalize_doc_id


def test_first_id_when_none_exist():
    """First doc in a project should get suffix 001."""
    result = compute_next_id([], "PRJ", "REQ")
    assert result == "PRJ-REQ-001"


def test_sequential_ids():
    """Next ID after existing 001, 002, 003 should be 004."""
    result = compute_next_id(["PRJ-REQ-001", "PRJ-REQ-002", "PRJ-REQ-003"], "PRJ", "REQ")
    assert result == "PRJ-REQ-004"


def test_gap_after_deletion():
    """After deleting 002, next should be 004 (not 003) since MAX is 003."""
    result = compute_next_id(["PRJ-REQ-001", "PRJ-REQ-003"], "PRJ", "REQ")
    assert result == "PRJ-REQ-004"


def test_all_deleted_except_highest():
    """Even if only the highest remains, next builds from its suffix."""
    result = compute_next_id(["PRJ-REQ-010"], "PRJ", "REQ")
    assert result == "PRJ-REQ-011"


def test_different_type_codes():
    """Verify various type codes produce correct prefix."""
    for type_code, expected in [
        ("TC", "PRJ-TC-001"),
        ("DES", "PRJ-DES-001"),
        ("RSK", "PRJ-RSK-001"),
        ("CHG", "PRJ-CHG-001"),
        ("TCO", "PRJ-TCO-001"),
        ("SPEC", "PRJ-SPEC-001"),
        ("PROT", "PRJ-PROT-001"),
        ("RPT", "PRJ-RPT-001"),
        ("STD", "PRJ-STD-001"),
        ("BL", "PRJ-BL-001"),
        ("TS", "PRJ-TS-001"),
    ]:
        result = compute_next_id([], "PRJ", type_code)
        assert result == expected, f"Failed for type_code={type_code}"


def test_ignores_malformed_ids():
    """Malformed IDs (non-numeric suffix) are gracefully skipped."""
    result = compute_next_id(["PRJ-REQ-001", "PRJ-REQ-abc", "PRJ-REQ-003"], "PRJ", "REQ")
    assert result == "PRJ-REQ-004"


def test_ignores_wrong_project_or_type_prefixes():
    """Only exact PROJECT-TYPE matches can advance the sequence."""
    result = compute_next_id(
        ["PRJ-REQ-001", "OTHER-REQ-099", "PRJ-TC-050", "PRJ-REQ-002-extra"],
        "PRJ",
        "REQ",
    )
    assert result == "PRJ-REQ-002"


def test_different_project_prefix():
    """Works with another three-letter project prefix."""
    result = compute_next_id(["VCU-TC-005", "VCU-TC-012"], "VCU", "TC")
    assert result == "VCU-TC-013"


def test_sequence_stops_at_999():
    """The PRJ-TYP-XXX convention only permits three numeric suffix digits."""
    with pytest.raises(ValueError, match="maximum is 999"):
        compute_next_id(["PRJ-REQ-999"], "PRJ", "REQ")


def test_import_scenario_bulk_ids():
    """Simulates bulk import: existing IDs + gap should yield max+1."""
    existing = ["PRJ-REQ-001", "PRJ-REQ-002", "PRJ-REQ-005"]
    result = compute_next_id(existing, "PRJ", "REQ")
    assert result == "PRJ-REQ-006"


def test_empty_string_id_ignored():
    """Empty strings in the list don't cause crashes."""
    result = compute_next_id(["", "PRJ-REQ-001"], "PRJ", "REQ")
    assert result == "PRJ-REQ-002"


def test_only_malformed_ids():
    """If all existing IDs are malformed, start from 001."""
    result = compute_next_id(["PRJ-REQ-abc", "PRJ-REQ-", "PRJ-REQ-xyz"], "PRJ", "REQ")
    assert result == "PRJ-REQ-001"


def test_zero_padded_consistency():
    """Result is always zero-padded to at least 3 digits."""
    result = compute_next_id([], "PRJ", "REQ")
    assert result == "PRJ-REQ-001"
    assert len(result.split("-")[-1]) == 3

    result2 = compute_next_id(["PRJ-REQ-098"], "PRJ", "REQ")
    assert result2 == "PRJ-REQ-099"
    assert len(result2.split("-")[-1]) == 3


def test_rejects_project_prefix_that_is_not_three_letters():
    with pytest.raises(ValueError, match="exactly three uppercase letters"):
        compute_next_id([], "BLOOM", "REQ")


def test_rejects_unsupported_type_code():
    with pytest.raises(ValueError, match="Unsupported document type code"):
        compute_next_id([], "PRJ", "BUG")


def test_normalizes_creator_supplied_doc_id():
    assert normalize_doc_id(" prj-req-001 ", expected_type_code="REQ") == "PRJ-REQ-001"


def test_rejects_creator_supplied_doc_id_with_wrong_project_prefix():
    with pytest.raises(ValueError, match="ID project prefix must be VCU"):
        normalize_doc_id("PRJ-REQ-001", expected_type_code="REQ", expected_project_prefix="VCU")
