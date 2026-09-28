"""Effective project permissions: the role baseline plus the policies of the user's groups.

The instance roles are unchanged. A direct member keeps exactly what the role allowed
before groups existed: an admin everything, a maintainer member every project action,
any other member view and comment. A group granted the project
adds its policy's (action x resource) matrix, including what the policy inherits from
its parent. Groups only add; they never take away what the role baseline gives.

A resource is a document type (REQ, TC, SPEC, ...) or one of the project objects that
are not documents: baseline, parameter and link.
"""

from typing import Optional

from app.schemas.memberships import EXTERNAL_DOC_TYPES

ANY = "*"

DOC_TYPE_RESOURCES = tuple(sorted(EXTERNAL_DOC_TYPES))
OBJECT_RESOURCES = ("baseline", "parameter", "link")
RESOURCES = DOC_TYPE_RESOURCES + OBJECT_RESOURCES
ACTIONS = (
    "view",
    "comment",
    "create",
    "edit",
    "delete",
    "review",
    "approve",
    "execute",
    "plan",
    "import",
    "export",
)


_DECISION_STATES = {"Approved", "Rejected"}
_REVIEW_STATES = {"Review", "Analysis"}

Permissions = dict[str, set[str]]


def role_baseline(instance_role: str, membership_role: Optional[str]) -> Permissions:
    """What the unchanged role gates allow on a project, as a permission matrix."""
    if instance_role == "admin":
        return {ANY: {ANY}}
    if membership_role is None:
        return {}
    if instance_role == "maintainer" and membership_role == "maintainer":
        return {resource: {ANY} for resource in RESOURCES}
    return {resource: {"view", "comment"} for resource in RESOURCES if resource != "parameter"}


def merge(into: Permissions, matrix: Optional[dict]) -> Permissions:
    """Union a stored {resource: [action, ...]} matrix into a permission set."""
    for resource, actions in (matrix or {}).items():
        into.setdefault(resource, set()).update(actions or [])
    return into


def has_permission(permissions: Permissions, action: str, resource: str) -> bool:
    """True when the set allows the action on the resource, directly or by wildcard."""
    granted = permissions.get(resource, set()) | permissions.get(ANY, set())
    return action in granted or ANY in granted


def transition_action(current_status: str, next_status: str) -> str:
    """The action a status transition needs: approve for a decision, review from a
    review state, edit otherwise (an author submitting or reopening)."""
    if next_status in _DECISION_STATES:
        return "approve"
    if current_status in _REVIEW_STATES:
        return "review"
    return "edit"


def as_lists(permissions: Permissions) -> dict[str, list[str]]:
    """A permission set as sorted lists, for a response body."""
    return {resource: sorted(actions) for resource, actions in sorted(permissions.items())}


def invalid_entries(matrix: dict) -> list[str]:
    """The resources and actions of a policy matrix that the vocabulary does not know."""
    known_resources = set(RESOURCES) | {ANY}
    known_actions = set(ACTIONS) | {ANY}
    problems: list[str] = []
    for resource, actions in matrix.items():
        if resource not in known_resources:
            problems.append(f"unknown resource {resource!r}")
        if not isinstance(actions, list):
            problems.append(f"actions for {resource!r} must be a list")
            continue
        problems.extend(
            f"unknown action {action!r} on {resource!r}"
            for action in actions
            if action not in known_actions
        )
    return problems
