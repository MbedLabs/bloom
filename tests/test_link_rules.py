import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.core.link_rules import (
    get_allowed_link_roles,
    is_allowed_link_role,
    is_allowed_tag_pair,
    is_known_linkable_type,
    is_tag_host_type,
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


def test_only_prose_bodies_host_tags():
    for kind in ("REQ", "DES", "RSK", "CHG", "CPT", "SPEC", "PRT", "RPT", "STD"):
        assert is_tag_host_type(kind) is True, kind
    for kind in ("TC", "TS", "CMP", "DEF", "other"):
        assert is_tag_host_type(kind) is False, kind


def test_tags_reach_pairs_the_link_matrix_has_no_row_for():
    assert is_allowed_link_role("SPEC", "REQ", "references") is False
    assert is_allowed_tag_pair("SPEC", "REQ") is True

    assert is_allowed_link_role("REQ", "REQ", "references") is False
    assert is_allowed_tag_pair("REQ", "REQ") is True

    assert is_allowed_link_role("REQ", "DES", "references") is False
    assert is_allowed_tag_pair("REQ", "DES") is True


def test_containers_are_taggable_but_never_tag():
    assert is_allowed_tag_pair("REQ", "CMP") is True
    assert is_allowed_tag_pair("REQ", "TS") is True
    assert is_allowed_tag_pair("REQ", "TC") is True
    assert is_allowed_tag_pair("CMP", "REQ") is False
    assert is_allowed_tag_pair("TS", "REQ") is False
    assert is_allowed_tag_pair("TC", "REQ") is False


def test_unknown_kinds_are_not_taggable():
    assert is_allowed_tag_pair("REQ", "other") is False
    assert is_allowed_tag_pair("other", "REQ") is False
