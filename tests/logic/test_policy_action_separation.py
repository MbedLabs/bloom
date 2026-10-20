"""Permission fields grant their own supported operations."""

import asyncio

import pytest

from app.api.policies import _apply_rules, _validate_rules, policy_rules
from app.core.permissions import (
    DOC_TYPE_RESOURCES,
    EXTERNAL_DENIED_ACTIONS,
    actions_for_rule,
    actions_on,
    has_permission,
    rule_of,
)
from app.models.groups import Policy
from app.schemas.groups import PolicyRule


def test_write_cannot_approve_or_delete():
    actions = set(actions_for_rule("REQ", True, True))
    assert {"create", "edit", "view"} <= actions
    assert not {"review", "approve", "delete"} & actions


def test_approval_and_deletion_do_not_manufacture_read_or_write():
    actions = set(actions_for_rule("REQ", False, False, True, approve=True))
    assert actions == {"review", "approve", "delete"}


def test_write_includes_read_without_approve_or_delete():
    actions = set(actions_for_rule("REQ", False, True))
    assert {"view", "comment", "create", "edit"} <= actions
    assert not {"approve", "review", "delete"} & actions


def test_stored_write_includes_read_without_rewriting_its_matrix():
    matrix = {"REQ": ["edit"]}
    assert actions_on(matrix, "REQ") == {"view", "comment", "edit"}
    assert rule_of(["edit"]) == (True, True, False, False, False)
    assert has_permission(matrix, "view", "REQ")
    assert not has_permission(matrix, "view", "TC")
    assert not has_permission(matrix, "approve", "REQ")
    assert matrix == {"REQ": ["edit"]}


@pytest.mark.parametrize("resource", DOC_TYPE_RESOURCES)
def test_review_is_independent_on_every_document_type(resource):
    actions = actions_for_rule(resource, False, False, review=True)
    assert actions == ["review"]
    matrix = {resource: actions}
    assert has_permission(matrix, "review", resource)
    assert not any(
        has_permission(matrix, action, resource)
        for action in ["view", "comment", "create", "edit", "approve", "delete"]
    )


def test_review_rule_roundtrips_without_read_write_approve_or_delete():
    policy = Policy(name="Review only", scope="document", permissions={}, type_tags={})
    rule = PolicyRule(review=True, visibility=["customer"])
    _apply_rules(policy, {"REQ": rule})
    assert policy.permissions == {"REQ": ["review"]}
    assert policy.type_tags == {"REQ": {"all": False, "visibility": ["customer"], "tags": []}}
    shown = policy_rules(policy)["REQ"]
    assert shown.review is True
    assert shown.read is shown.write is shown.approve is shown.delete is False
    _apply_rules(policy, {"REQ": shown})
    assert policy.permissions == {"REQ": ["review"]}


def test_review_rule_requires_an_origin_without_granting_read():
    from fastapi import HTTPException

    rule = PolicyRule(review=True)
    validation = _validate_rules(None, {"REQ": rule})
    with pytest.raises(HTTPException, match="Choose at least one tag for REQ"):
        asyncio.run(validation)


@pytest.mark.parametrize(
    "resource", ["baseline", "parameter", "link", "project", "users", "access", "application"]
)
def test_review_is_not_a_project_or_application_operation(resource):
    from fastapi import HTTPException

    validation = _validate_rules(None, {resource: PolicyRule(review=True)}, "app")
    with pytest.raises(HTTPException, match=f"Review is not supported on {resource}"):
        asyncio.run(validation)


@pytest.mark.parametrize("resource", ["STD", "RSK", "CMP"])
def test_review_does_not_make_exception_approval_supported(resource):
    from fastapi import HTTPException

    validation = _validate_rules(None, {resource: PolicyRule(approve=True, all_origins=True)})
    with pytest.raises(HTTPException, match=f"Approve is not supported on {resource}"):
        asyncio.run(validation)


def test_external_review_is_permitted_without_approval_or_deletion():
    assert "review" not in EXTERNAL_DENIED_ACTIONS
    assert {"approve", "delete"} <= EXTERNAL_DENIED_ACTIONS


@pytest.mark.parametrize("resource", ["RPT", "STD", "RSK", "CMP"])
def test_write_and_approval_do_not_add_new_exception_review_authority(resource):
    assert "review" not in actions_for_rule(resource, True, True, True, approve=True)


def test_external_review_term_retains_customer_scope_without_read():
    from app.core.security import _policy_terms

    policy = Policy(
        name="Customer reviewer",
        scope="project",
        permissions={"STD": ["review", "approve", "delete"]},
        type_tags={"STD": {"all": True, "visibility": [], "tags": []}},
    )
    terms = _policy_terms(policy, external=True)
    assert len(terms) == 1
    assert terms[0].permissions == {"STD": {"review"}}
    assert terms[0].customer_only is True
    assert terms[0].doc_types == frozenset({"STD"})
