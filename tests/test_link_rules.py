import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.core.link_rules import (
    get_allowed_link_roles,
    is_allowed_link_role,
    is_known_linkable_type,
    normalize_linkable_type,
)


def test_normalize_linkable_type_maps_known_values():
    assert normalize_linkable_type("req") == "REQ"
    assert normalize_linkable_type("spec") == "SPEC"


def test_get_allowed_link_roles_uses_only_explicit_matrix_rows():
    assert get_allowed_link_roles("TC", "REQ") == ("verifies",)
    assert get_allowed_link_roles("DES", "REQ") == ("satisfies", "implements", "references")
    assert get_allowed_link_roles("TC", "DES") == ()
    assert get_allowed_link_roles("CPT", "TC") == ("implements",)
    assert get_allowed_link_roles("CPT", "SPEC") == ("covers", "verifies", "references")
    assert get_allowed_link_roles("CPT", "REQ") == ("covers", "verifies", "references")
    assert get_allowed_link_roles("REQ", "SPEC") == ("derives_from", "refines", "references")
    assert get_allowed_link_roles("SPEC", "REQ") == ()
    assert get_allowed_link_roles("CMP", "REQ") == ("covers", "references")
    assert get_allowed_link_roles("CMP", "SPEC") == ("verifies", "references")
    assert get_allowed_link_roles("TS", "REQ") == ("covers", "references")
    assert get_allowed_link_roles("TS", "TC") == ("contains", "references")


def test_link_rule_helpers_recognize_supported_types_and_roles():
    assert is_known_linkable_type("TC") is True
    assert is_known_linkable_type("STD") is True
    assert is_known_linkable_type("TS") is True
    assert is_known_linkable_type("other") is False

    assert is_allowed_link_role("TC", "REQ", "verifies") is True
    assert is_allowed_link_role("TC", "REQ", "references") is False
    assert is_allowed_link_role("TC", "DES", "relates_to") is False
    assert is_allowed_link_role("CPT", "TC", "implements") is True
    assert is_allowed_link_role("TS", "TC", "contains") is True
    assert is_allowed_link_role("CMP", "REQ", "verifies") is False
