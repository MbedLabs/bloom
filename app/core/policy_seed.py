"""Default policies (the shipped personas). Migration 7dbc5eb75da5 seeds them.

Each default Policy carries is_default=True: an instance base_role plus an
(action x resource) matrix. The base_role drives project access through group
grants (see require_project_access); the matrix is stored but not yet enforced.
Defaults are protected: undeletable and their base_role is fixed.
"""

from app.schemas.memberships import DEFAULT_EXTERNAL_DOC_TYPES

_ARTEFACTS = [
    "requirement",
    "design",
    "test_concept",
    "test_case",
    "risk",
    "change_request",
    "defect",
    "document",
    "suite",
    "campaign",
    "run",
    "baseline",
]


def _all(*actions: str) -> dict:
    return {r: list(actions) for r in _ARTEFACTS}


def _merge(base: dict, overrides: dict) -> dict:
    merged = dict(base)
    merged.update(overrides)
    return merged


# name -> (base_role, description, permissions, doc_tag_scope). base_role is one of
# the unchanged instance roles (admin, maintainer, external).
DEFAULT_POLICIES = [
    {
        "name": "Administrator",
        "base_role": "admin",
        "description": "Full instance control: users, groups, policies, integrations, branding, every project.",
        "permissions": {"*": ["*"]},
        "doc_tag_scope": None,
    },
    {
        "name": "Product Owner",
        "base_role": "maintainer",
        "description": "Owns requirements and specifications; authors and approves requirements, specs and change requests.",
        "permissions": _merge(
            _all("view", "comment"),
            {
                "requirement": ["view", "comment", "create", "edit", "approve"],
                "document": ["view", "comment", "create", "edit", "approve"],
                "change_request": ["view", "comment", "create", "edit", "approve"],
                "risk": ["view", "comment", "create", "edit"],
            },
        ),
        "doc_tag_scope": None,
    },
    {
        "name": "Project Manager",
        "base_role": "maintainer",
        "description": "Plans and baselines, manages members and reports, owns the risk register, approves change requests.",
        "permissions": _merge(
            _all("view", "comment"),
            {
                "change_request": ["view", "comment", "create", "edit", "review", "approve"],
                "risk": ["view", "comment", "create", "edit", "review"],
                "campaign": ["view", "comment", "plan"],
                "suite": ["view", "comment", "plan"],
                "baseline": ["view", "comment", "create", "approve"],
                "requirement": ["view", "comment", "review"],
                "member": ["view", "manage"],
            },
        ),
        "doc_tag_scope": None,
    },
    {
        "name": "Business Analyst",
        "base_role": "maintainer",
        "description": "Authors requirements, specifications and risks; comments on design and tests.",
        "permissions": _merge(
            _all("view", "comment"),
            {
                "requirement": ["view", "comment", "create", "edit"],
                "document": ["view", "comment", "create", "edit"],
                "risk": ["view", "comment", "create", "edit"],
            },
        ),
        "doc_tag_scope": None,
    },
    {
        "name": "Developer",
        "base_role": "maintainer",
        "description": "Authors design; creates and resolves defects; cannot approve requirements.",
        "permissions": _merge(
            _all("view", "comment"),
            {
                "design": ["view", "comment", "create", "edit"],
                "defect": ["view", "comment", "create", "edit"],
            },
        ),
        "doc_tag_scope": None,
    },
    {
        "name": "QA/Test Engineer",
        "base_role": "maintainer",
        "description": "Authors test concepts and cases, plans suites and campaigns, executes runs, logs defects.",
        "permissions": _merge(
            _all("view", "comment"),
            {
                "test_concept": ["view", "comment", "create", "edit"],
                "test_case": ["view", "comment", "create", "edit"],
                "suite": ["view", "comment", "create", "edit", "plan"],
                "campaign": ["view", "comment", "create", "edit", "plan"],
                "run": ["view", "comment", "execute"],
                "defect": ["view", "comment", "create"],
            },
        ),
        "doc_tag_scope": None,
    },
    {
        "name": "Reviewer/Approver",
        "base_role": "maintainer",
        "description": "Reviews and approves any artefact and comments; no authoring.",
        "permissions": _all("view", "comment", "review", "approve"),
        "doc_tag_scope": None,
    },
    {
        "name": "Customer/Stakeholder",
        "base_role": "external",
        "description": "Views and comments on customer-visible artefacts of the allowed document types.",
        "permissions": _all("view", "comment"),
        # doc_tag_scope is the external document-type allowlist (the same codes a
        # direct external membership uses); None would mean every type.
        "doc_tag_scope": sorted(DEFAULT_EXTERNAL_DOC_TYPES),
    },
    {
        "name": "Viewer",
        "base_role": "maintainer",
        "description": "Views internal artefacts; read-only.",
        "permissions": _all("view"),
        "doc_tag_scope": None,
    },
]
