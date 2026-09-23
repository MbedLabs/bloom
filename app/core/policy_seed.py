"""Default policies (the shipped personas). Migration 7dbc5eb75da5 seeds them.

Each default Policy carries is_default=True: an instance base_role plus an
(action x resource) matrix. The base_role drives project access through group
grants (see require_project_access); require_permission enforces the matrix.
Defaults are protected: undeletable and their base_role is fixed.
"""

from app.core.permissions import RESOURCES
from app.schemas.memberships import DEFAULT_EXTERNAL_DOC_TYPES

_ARTEFACTS = list(RESOURCES)
_AUTHOR = ["view", "comment", "create", "edit", "delete"]
_LINKS = {"link": _AUTHOR}


def _all(*actions: str) -> dict:
    return {r: list(actions) for r in _ARTEFACTS}


def _merge(base: dict, overrides: dict) -> dict:
    merged = dict(base)
    merged.update(overrides)
    return merged


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
                "requirement": _AUTHOR + ["approve", "import", "export"],
                "document": _AUTHOR + ["approve", "import"],
                "change_request": _AUTHOR + ["approve"],
                "risk": _AUTHOR,
                "parameter": _AUTHOR,
                **_LINKS,
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
                "change_request": _AUTHOR + ["review", "approve"],
                "risk": _AUTHOR + ["review"],
                "campaign": _AUTHOR + ["plan"],
                "suite": ["view", "comment", "plan"],
                "baseline": _AUTHOR + ["approve"],
                "requirement": ["view", "comment", "review", "export"],
                "test_case": ["view", "comment", "export"],
                "member": ["view", "manage"],
                **_LINKS,
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
                "requirement": _AUTHOR + ["import", "export"],
                "document": _AUTHOR + ["import"],
                "risk": _AUTHOR,
                "parameter": _AUTHOR,
                **_LINKS,
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
                "design": _AUTHOR,
                "defect": _AUTHOR,
                **_LINKS,
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
                "test_concept": _AUTHOR,
                "test_case": _AUTHOR + ["import", "export"],
                "suite": _AUTHOR + ["plan"],
                "campaign": _AUTHOR + ["plan"],
                "run": ["view", "comment", "execute"],
                "defect": ["view", "comment", "create"],
                "parameter": _AUTHOR,
                **_LINKS,
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
        "permissions": {r: ["view", "comment"] for r in _ARTEFACTS if r != "parameter"},
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
