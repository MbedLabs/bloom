"""The default catalogue covers Bloom resources with independently scoped permissions."""

import copy
import importlib.util
from pathlib import Path

import pytest

from app.core.permissions import DOC_TYPE_RESOURCES, RESOURCE_ACTIONS, RESOURCES
from app.core.policy_seed import DEFAULT_GROUPS, DEFAULT_POLICIES

DOCUMENT_POLICIES = {
    "Requirements": "REQ",
    "Specifications": "SPEC",
    "Standards": "STD",
    "Designs": "DES",
    "Risks": "RSK",
    "Change Requests": "CHG",
    "Concepts": "CPT",
    "Test Cases": "TC",
    "Suites": "TS",
    "Campaigns": "CMP",
    "Defects": "DEF",
    "Protocols": "PRT",
    "Reports": "RPT",
    "Visions": "VIS",
}


def test_twenty_four_defaults_have_exact_resource_scopes_and_supported_permissions():
    policies = {policy["name"]: policy for policy in DEFAULT_POLICIES}
    assert len(DEFAULT_POLICIES) == len(policies) == 24
    assert set(policies) == set(DOCUMENT_POLICIES) | {
        "Baselines",
        "Parameters",
        "Traceability",
        "Project Management",
        "Read Internal",
        "Read Customer",
        "Review Internal",
        "Review Customer",
        "Access Management",
        "Application Administration",
    }
    assert set(DOCUMENT_POLICIES.values()) == set(DOC_TYPE_RESOURCES)
    for name, resource in DOCUMENT_POLICIES.items():
        policy = policies[name]
        assert policy["scope"] == "document"
        assert set(policy["permissions"]) == {resource}
        expected = RESOURCE_ACTIONS[resource] - (
            {"review"} if resource in {"RPT", "STD", "RSK", "CMP"} else set()
        )
        assert set(policy["permissions"][resource]) == expected
        assert policy["type_tags"][resource] == {
            "all": True,
            "visibility": [],
            "tags": [],
        }
    for name, resource in [
        ("Baselines", "baseline"),
        ("Parameters", "parameter"),
        ("Traceability", "link"),
        ("Project Management", "project"),
    ]:
        policy = policies[name]
        assert policy["scope"] == "project"
        assert set(policy["permissions"]) == {resource}
        assert set(policy["permissions"][resource]) == RESOURCE_ACTIONS[resource]
    for name, origin in [("Read Internal", None), ("Read Customer", "customer")]:
        policy = policies[name]
        assert policy["scope"] == "project"
        assert set(policy["permissions"]) == set(RESOURCES)
        assert all(
            set(actions) <= {"view", "comment"} for actions in policy["permissions"].values()
        )
        assert all(
            rule == {"all": origin is None, "visibility": [origin] if origin else [], "tags": []}
            for rule in policy["type_tags"].values()
        )
    access = policies["Access Management"]
    assert access["scope"] == "app"
    assert set(access["permissions"]) == {"access"}
    assert set(access["permissions"]["access"]) == RESOURCE_ACTIONS["access"]
    assert access["type_tags"] == {}
    admin = policies["Application Administration"]
    assert admin["scope"] == "app"
    assert {resource: set(actions) for resource, actions in admin["permissions"].items()} == {
        resource: actions for resource, actions in RESOURCE_ACTIONS.items()
    }


def test_default_groups_are_populated_without_people_or_project_assignments():
    policies = {policy["name"] for policy in DEFAULT_POLICIES}
    assert {group["name"] for group in DEFAULT_GROUPS} == {
        "Product Owners",
        "Developers",
        "Testers",
        "Administrators",
        "Customers",
    }
    for group in DEFAULT_GROUPS:
        assert group["policy_names"]
        assert len(group["policy_names"]) == len(set(group["policy_names"]))
        assert set(group["policy_names"]) <= policies
        assert not {"user_ids", "project_ids"} & group.keys()
        if group["name"] == "Customers":
            assert group["policy_names"] == ["Read Customer"]
        elif group["name"] != "Administrators":
            assert {"Read Internal", "Read Customer"} <= set(group["policy_names"])


def _migration(name: str):
    path = Path(__file__).resolve().parents[2] / "alembic/versions" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_release_and_visions_migrations_freeze_the_runtime_catalogue():
    release = _migration("c5e8a1f2b9d4_access_entries.py")
    visions = _migration("637f976e78e0_visions.py")
    expected = {policy["name"]: copy.deepcopy(policy) for policy in release.DEFAULT_POLICIES}
    for name in visions.COVERED_POLICIES:
        expected[name]["permissions"]["VIS"] = list(expected[name]["permissions"]["SPEC"])
        expected[name]["type_tags"]["VIS"] = dict(expected[name]["type_tags"]["SPEC"])
    expected[visions.VISIONS] = {
        "name": visions.VISIONS,
        "description": "",
        "scope": "document",
        "permissions": {"VIS": visions.VIS_ACTIONS},
        "type_tags": {"VIS": {"all": True, "visibility": [], "tags": []}},
    }
    assert {policy["name"]: policy for policy in DEFAULT_POLICIES} == expected
    groups = {group["name"]: copy.deepcopy(group) for group in release.DEFAULT_GROUPS}
    owners = groups[visions.PRODUCT_OWNERS]["policy_names"]
    owners.insert(owners.index("Specifications") + 1, visions.VISIONS)
    assert {group["name"]: group for group in DEFAULT_GROUPS} == groups
    released_maintainer_set = {
        policy["name"]
        for policy in release.DEFAULT_POLICIES
        if policy["scope"] in {"document", "project"}
        and policy["name"]
        not in {"Read Internal", "Read Customer", "Review Internal", "Review Customer"}
    }
    assert set(visions.RELEASED_MAINTAINER_SET) == released_maintainer_set


@pytest.mark.parametrize(
    "name,origin", [("Review Internal", None), ("Review Customer", "customer")]
)
def test_reviewer_defaults_grant_only_review_on_all_document_types(name, origin):
    policy = next(policy for policy in DEFAULT_POLICIES if policy["name"] == name)
    assert policy["scope"] == "project"
    assert policy["permissions"] == {resource: ["review"] for resource in DOC_TYPE_RESOURCES}
    assert policy["type_tags"] == {
        resource: {"all": origin is None, "visibility": [origin] if origin else [], "tags": []}
        for resource in DOC_TYPE_RESOURCES
    }
    assert all(name not in group["policy_names"] for group in DEFAULT_GROUPS)
