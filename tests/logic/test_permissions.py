"""The permission vocabulary: role baselines, policy matrices and transition actions."""

from app.core.permissions import (
    ANY,
    RESOURCES,
    as_lists,
    has_permission,
    invalid_entries,
    merge,
    role_baseline,
    transition_action,
)


def test_role_baseline_matches_the_role_gates():
    assert role_baseline("admin", None) == {ANY: {ANY}}
    assert role_baseline("maintainer", None) == {}
    maintainer = role_baseline("maintainer", "maintainer")
    assert set(maintainer) == set(RESOURCES)
    assert has_permission(maintainer, "delete", "REQ")
    assert not has_permission(maintainer, "manage", "member")
    for instance, member in (
        ("external", "external"),
        ("maintainer", "external"),
        ("external", "maintainer"),
    ):
        reader = role_baseline(instance, member)
        assert has_permission(reader, "view", "REQ")
        assert has_permission(reader, "comment", "TC")
        assert not has_permission(reader, "edit", "REQ")
        assert not has_permission(reader, "view", "parameter")


def test_merge_only_adds():
    permissions = role_baseline("external", "external")
    merge(permissions, {"TC": ["create"], "member": ["view"]})
    merge(permissions, None)
    assert has_permission(permissions, "create", "TC")
    assert has_permission(permissions, "view", "TC")
    assert has_permission(permissions, "view", "member")
    assert not has_permission(permissions, "create", "REQ")


def test_wildcards():
    assert has_permission({ANY: {"view"}}, "view", "DES")
    assert not has_permission({ANY: {"view"}}, "edit", "DES")
    assert has_permission({"DES": {ANY}}, "approve", "DES")
    assert not has_permission({}, "view", "DES")


def test_transition_action():
    assert transition_action("Draft", "Review") == "edit"
    assert transition_action("Review", "Draft") == "review"
    assert transition_action("Analysis", "Implemented") == "review"
    assert transition_action("Review", "Approved") == "approve"
    assert transition_action("Submitted", "Rejected") == "approve"
    assert transition_action("Open", "Closed") == "edit"


def test_invalid_entries_and_lists():
    assert invalid_entries({"REQ": ["view"], ANY: [ANY], "member": ["manage"]}) == []
    assert invalid_entries({"widget": ["view"], "DES": ["fly"], "RSK": "view"}) == [
        "unknown resource 'widget'",
        "unknown action 'fly' on 'DES'",
        "actions for 'RSK' must be a list",
    ]
    assert as_lists({"RSK": {"view", "edit"}, ANY: {"view"}}) == {
        ANY: ["view"],
        "RSK": ["edit", "view"],
    }
