"""Bloom's scoped default policies and initial editable policy groups."""

from app.core.permissions import (
    DOC_TYPE_RESOURCES,
    POLICY_RESOURCES,
    RESOURCES,
    actions_for_rule,
)

READ_CUSTOMER = "Read Customer"
READ_INTERNAL = "Read Internal"

DOCUMENT_POLICIES = (
    ("Requirements", "REQ"),
    ("Specifications", "SPEC"),
    ("Standards", "STD"),
    ("Designs", "DES"),
    ("Risks", "RSK"),
    ("Change Requests", "CHG"),
    ("Concepts", "CPT"),
    ("Test Cases", "TC"),
    ("Suites", "TS"),
    ("Campaigns", "CMP"),
    ("Defects", "DEF"),
    ("Protocols", "PRT"),
    ("Reports", "RPT"),
    ("Visions", "VIS"),
)


def _policy(
    name: str,
    scope: str,
    resources: tuple,
    read_only: bool = False,
    origin: str | None = None,
    review_only: bool = False,
    review_all: bool = False,
) -> dict:
    """Build supported resource permissions with the selected document origins."""
    permissions = {
        resource: actions_for_rule(
            resource,
            not review_only,
            not (read_only or review_only),
            not (read_only or review_only),
            review=review_only or (review_all and resource in DOC_TYPE_RESOURCES),
            approve=not (read_only or review_only),
        )
        for resource in resources
    }
    return {
        "name": name,
        "description": "",
        "scope": scope,
        "permissions": permissions,
        "type_tags": {
            resource: {"all": origin is None, "visibility": [origin] if origin else [], "tags": []}
            for resource in resources
            if resource in DOC_TYPE_RESOURCES
        },
    }


DEFAULT_POLICIES = [
    *(_policy(name, "document", (resource,)) for name, resource in DOCUMENT_POLICIES),
    _policy("Baselines", "project", ("baseline",)),
    _policy("Parameters", "project", ("parameter",)),
    _policy("Traceability", "project", ("link",)),
    _policy("Project Management", "project", ("project",)),
    _policy(READ_INTERNAL, "project", RESOURCES, read_only=True),
    _policy(READ_CUSTOMER, "project", RESOURCES, read_only=True, origin="customer"),
    _policy("Review Internal", "project", DOC_TYPE_RESOURCES, review_only=True),
    _policy("Review Customer", "project", DOC_TYPE_RESOURCES, review_only=True, origin="customer"),
    _policy("Access Management", "app", ("access",)),
    _policy("Application Administration", "app", POLICY_RESOURCES, review_all=True),
]

DEFAULT_GROUPS = [
    {
        "name": "Customers",
        "description": "",
        "policy_names": [READ_CUSTOMER],
    },
    {
        "name": "Product Owners",
        "description": "",
        "policy_names": [
            READ_INTERNAL,
            READ_CUSTOMER,
            "Requirements",
            "Specifications",
            "Visions",
            "Standards",
            "Risks",
            "Change Requests",
            "Baselines",
            "Parameters",
            "Traceability",
        ],
    },
    {
        "name": "Developers",
        "description": "",
        "policy_names": [
            READ_INTERNAL,
            READ_CUSTOMER,
            "Designs",
            "Baselines",
            "Parameters",
            "Traceability",
        ],
    },
    {
        "name": "Testers",
        "description": "",
        "policy_names": [
            READ_INTERNAL,
            READ_CUSTOMER,
            "Concepts",
            "Test Cases",
            "Suites",
            "Campaigns",
            "Defects",
            "Protocols",
            "Reports",
            "Baselines",
            "Parameters",
            "Traceability",
        ],
    },
    {
        "name": "Administrators",
        "description": "",
        "policy_names": ["Application Administration", "Project Management"],
    },
]
