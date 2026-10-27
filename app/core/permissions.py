"""Project action vocabulary, policy matrices, Write-implied reading
and role-baseline conversion."""

from typing import Optional

from app.schemas.memberships import EXTERNAL_DOC_TYPES

ANY = "*"

DOC_TYPE_RESOURCES = tuple(sorted(EXTERNAL_DOC_TYPES))
OBJECT_RESOURCES = ("baseline", "parameter", "link", "project")
RESOURCES = DOC_TYPE_RESOURCES + OBJECT_RESOURCES
APP_RESOURCES = ("users", "access", "application")
POLICY_RESOURCES = RESOURCES + APP_RESOURCES
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

RESOURCE_ACTIONS = {
    "REQ": frozenset(
        {"view", "comment", "create", "edit", "delete", "review", "approve", "import", "export"}
    ),
    "TC": frozenset(
        {"view", "comment", "create", "edit", "delete", "review", "approve", "import", "export"}
    ),
    "SPEC": frozenset(
        {"view", "comment", "create", "edit", "delete", "review", "approve", "import"}
    ),
    "PRT": frozenset(
        {"view", "comment", "create", "edit", "delete", "review", "approve", "import"}
    ),
    "RPT": frozenset(
        {"view", "comment", "create", "edit", "delete", "review", "approve", "import"}
    ),
    "STD": frozenset({"view", "comment", "create", "edit", "delete", "review", "import"}),
    "VIS": frozenset(
        {"view", "comment", "create", "edit", "delete", "review", "approve", "import"}
    ),
    "DES": frozenset({"view", "comment", "create", "edit", "delete", "review", "approve"}),
    "CHG": frozenset({"view", "comment", "create", "edit", "delete", "review", "approve"}),
    "CPT": frozenset({"view", "comment", "create", "edit", "delete", "review", "approve"}),
    "RSK": frozenset({"view", "comment", "create", "edit", "delete", "review"}),
    "DEF": frozenset({"view", "comment", "create", "edit", "delete", "review", "approve"}),
    "TS": frozenset({"view", "create", "edit", "delete", "review", "approve", "plan"}),
    "CMP": frozenset({"view", "create", "edit", "delete", "review", "execute", "plan"}),
    "baseline": frozenset({"view", "create", "edit", "delete"}),
    "parameter": frozenset({"view", "create", "edit", "delete"}),
    "link": frozenset({"view", "create", "delete"}),
    "project": frozenset({"view", "create", "edit"}),
    "users": frozenset({"view", "create", "edit", "delete"}),
    "access": frozenset({"view", "create", "edit", "delete"}),
    "application": frozenset({"view", "create", "edit", "delete"}),
}

READ_ACTIONS = frozenset({"view", "comment"})
WRITE_ACTIONS = frozenset({"create", "edit"})
APPROVE_ACTIONS = frozenset({"review", "approve"})
APPROVE_REVIEW_RESOURCES = frozenset(
    {"REQ", "TC", "SPEC", "PRT", "DES", "CHG", "CPT", "DEF", "TS", "VIS"}
)
EXTERNAL_DENIED_ACTIONS = frozenset({"approve", "delete"})
VISIBILITIES = ("internal", "customer")


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
    """Return whether the resource grants the action, including Read implied by Write."""
    granted = set(permissions.get(resource, set())) | set(permissions.get(ANY, set()))
    return (
        action in granted
        or ANY in granted
        or (
            action in READ_ACTIONS
            and bool(granted & WRITE_ACTIONS)
            and action in RESOURCE_ACTIONS.get(resource, READ_ACTIONS)
        )
    )


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
    known_resources = set(POLICY_RESOURCES) | {ANY}
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
        if resource in RESOURCE_ACTIONS:
            problems.extend(
                f"action {action!r} is not supported on {resource!r}"
                for action in actions
                if action in known_actions
                and action != ANY
                and action not in RESOURCE_ACTIONS[resource]
            )
    return problems


def actions_on(matrix: Optional[dict], resource: str) -> set[str]:
    """Resolve a resource's supported actions, wildcards and Write-implied reading."""
    stored = set((matrix or {}).get(resource) or []) | set((matrix or {}).get(ANY) or [])
    if ANY in stored:
        return set(RESOURCE_ACTIONS[resource])
    granted = stored & RESOURCE_ACTIONS[resource]
    if granted & WRITE_ACTIONS:
        granted |= READ_ACTIONS & RESOURCE_ACTIONS[resource]
    return granted


def rule_of(actions) -> tuple[bool, bool, bool, bool, bool]:
    """Return Read, Write, Review, Approve and Delete with Write including Read."""
    actions = set(actions)
    return (
        bool(actions & (READ_ACTIONS | WRITE_ACTIONS)),
        bool(actions & WRITE_ACTIONS),
        "review" in actions,
        "approve" in actions,
        "delete" in actions,
    )


def actions_for_rule(
    resource: str,
    read: bool,
    write: bool,
    delete: bool = False,
    *,
    review: bool = False,
    approve: bool = False,
) -> list[str]:
    """Map permission fields to supported operations, with Write including Read."""
    granted: set[str] = set()
    supported = RESOURCE_ACTIONS[resource]
    if read or write:
        granted |= supported & READ_ACTIONS
    if write:
        granted |= supported - READ_ACTIONS - APPROVE_ACTIONS - {"delete"}
    if review:
        granted |= supported & {"review"}
    if approve:
        granted |= supported & {"approve"}
        if resource in APPROVE_REVIEW_RESOURCES:
            granted.add("review")
    if delete:
        granted |= supported & {"delete"}
    return sorted(granted)
