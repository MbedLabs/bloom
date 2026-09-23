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
    assert has_permission(maintainer, "delete", "requirement")
    assert not has_permission(maintainer, "manage", "member")
    for instance, member in (
        ("external", "external"),
        ("maintainer", "external"),
        ("external", "maintainer"),
    ):
        reader = role_baseline(instance, member)
        assert has_permission(reader, "view", "requirement")
        assert has_permission(reader, "comment", "test_case")
        assert not has_permission(reader, "edit", "requirement")
        assert not has_permission(reader, "view", "parameter")


def test_merge_only_adds():
    permissions = role_baseline("external", "external")
    merge(permissions, {"test_case": ["create"], "member": ["view"]})
    merge(permissions, None)
    assert has_permission(permissions, "create", "test_case")
    assert has_permission(permissions, "view", "test_case")
    assert has_permission(permissions, "view", "member")
    assert not has_permission(permissions, "create", "requirement")


def test_wildcards():
    assert has_permission({ANY: {"view"}}, "view", "design")
    assert not has_permission({ANY: {"view"}}, "edit", "design")
    assert has_permission({"design": {ANY}}, "approve", "design")
    assert not has_permission({}, "view", "design")


def test_transition_action():
    assert transition_action("Draft", "Review") == "edit"
    assert transition_action("Review", "Draft") == "review"
    assert transition_action("Analysis", "Implemented") == "review"
    assert transition_action("Review", "Approved") == "approve"
    assert transition_action("Submitted", "Rejected") == "approve"
    assert transition_action("Open", "Closed") == "edit"


def test_invalid_entries_and_lists():
    assert invalid_entries({"requirement": ["view"], ANY: [ANY], "member": ["manage"]}) == []
    assert invalid_entries({"widget": ["view"], "design": ["fly"], "risk": "view"}) == [
        "unknown resource 'widget'",
        "unknown action 'fly' on 'design'",
        "actions for 'risk' must be a list",
    ]
    assert as_lists({"risk": {"view", "edit"}, ANY: {"view"}}) == {
        ANY: ["view"],
        "risk": ["edit", "view"],
    }
