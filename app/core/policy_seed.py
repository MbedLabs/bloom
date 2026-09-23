"""The default policies Bloom ships. Migration 7dbc5eb75da5 seeds them.

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
        "name": "Requirements Manager",
        "base_role": "maintainer",
        "description": "Create, edit, delete and approve requirements, specifications and change requests; edit risks and parameters; import and export requirements.",
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
        "name": "Project Administrator",
        "base_role": "maintainer",
        "description": "Manage project members, campaigns and baselines; review and approve change requests and risks; review requirements; export requirements and test cases.",
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
        "name": "Requirements Author",
        "base_role": "maintainer",
        "description": "Create, edit and delete requirements, specifications, risks and parameters; import and export requirements; view and comment on everything else.",
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
        "name": "Design Author",
        "base_role": "maintainer",
        "description": "Create, edit and delete designs and defects; view and comment on everything else.",
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
        "name": "Test Author",
        "base_role": "maintainer",
        "description": "Create, edit and delete test concepts, test cases, suites and campaigns; plan suites and campaigns; execute runs; log defects; import and export test cases.",
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
        "name": "Approver",
        "base_role": "maintainer",
        "description": "Review, approve and comment on every artefact; no create or edit.",
        "permissions": _all("view", "comment", "review", "approve"),
        "doc_tag_scope": None,
    },
    {
        "name": "External Reader",
        "base_role": "external",
        "description": "View and comment on customer-visible artefacts of the allowed document types.",
        "permissions": {r: ["view", "comment"] for r in _ARTEFACTS if r != "parameter"},
        "doc_tag_scope": sorted(DEFAULT_EXTERNAL_DOC_TYPES),
    },
    {
        "name": "Read Only",
        "base_role": "maintainer",
        "description": "View internal artefacts; no changes.",
        "permissions": _all("view"),
        "doc_tag_scope": None,
    },
]
