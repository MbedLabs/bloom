"""access entries

Revision ID: c5e8a1f2b9d4
Revises: e1a7c3f9b204
Create Date: 2026-10-08

Adds artefact creators, twenty-one scoped default policies, five editable groups with
policy bundles, origin labels and per-project access entries. Released internal
maintainer memberships keep full supported project and document operations through
scoped policies. Released read-only memberships keep their document-type and origin
restrictions without parameter access. Instance administrators remain global.
Downgrade drops what the upgrade added.
"""

from datetime import datetime

import sqlalchemy as sa

from alembic import op

revision = "c5e8a1f2b9d4"
down_revision = "e1a7c3f9b204"
branch_labels = None
depends_on = None

FROZEN_LINK_RULE_ROWS = (
    ("REQ", "REQ", ("derives_from", "refines", "depends_on", "duplicates", "relates_to")),
    ("REQ", "SPEC", ("derives_from", "refines", "references")),
    ("REQ", "STD", ("references",)),
    ("REQ", "TS", ("references",)),
    ("REQ", "CMP", ("references",)),
    ("SPEC", "SPEC", ("derives_from", "refines", "depends_on", "duplicates", "relates_to")),
    ("SPEC", "STD", ("references",)),
    ("STD", "STD", ("duplicates", "relates_to", "references")),
    ("CPT", "SPEC", ("covers", "verifies", "references")),
    ("CPT", "REQ", ("covers", "verifies", "references")),
    ("CPT", "TC", ("implements",)),
    ("CPT", "CPT", ("derives_from", "refines", "relates_to")),
    ("CPT", "STD", ("references",)),
    ("CPT", "TS", ("references",)),
    ("TC", "REQ", ("verifies",)),
    ("TC", "SPEC", ("verifies",)),
    ("TC", "PRT", ("implements", "references")),
    ("TC", "TC", ("depends_on", "duplicates", "relates_to")),
    ("TC", "STD", ("references",)),
    ("TC", "DEF", ("references",)),
    ("TS", "TC", ("contains", "references")),
    ("TS", "CPT", ("contains", "references")),
    ("TS", "SPEC", ("covers", "references")),
    ("TS", "REQ", ("covers", "references")),
    ("TS", "TS", ("relates_to",)),
    ("TS", "CMP", ("relates_to",)),
    ("CMP", "SPEC", ("verifies", "references")),
    ("CMP", "REQ", ("covers", "references")),
    ("CMP", "TC", ("contains", "references")),
    ("CMP", "CPT", ("contains", "references")),
    ("CMP", "TS", ("relates_to",)),
    ("CMP", "DEF", ("references",)),
    ("CMP", "CMP", ("relates_to",)),
    ("PRT", "REQ", ("verifies", "references")),
    ("PRT", "SPEC", ("verifies", "references")),
    ("PRT", "CPT", ("implements",)),
    ("PRT", "PRT", ("derives_from", "depends_on", "duplicates", "relates_to")),
    ("PRT", "STD", ("references",)),
    ("RPT", "REQ", ("references",)),
    ("RPT", "SPEC", ("references",)),
    ("RPT", "CPT", ("references",)),
    ("RPT", "TC", ("references",)),
    ("RPT", "TS", ("references",)),
    ("RPT", "CMP", ("references",)),
    ("RPT", "PRT", ("references",)),
    ("RPT", "DES", ("references",)),
    ("RPT", "RSK", ("references",)),
    ("RPT", "CHG", ("references",)),
    ("RPT", "STD", ("references",)),
    ("RPT", "DEF", ("references",)),
    ("RPT", "RPT", ("duplicates", "relates_to", "references")),
    ("DES", "REQ", ("satisfies", "implements", "references")),
    ("DES", "SPEC", ("implements", "references")),
    ("DES", "RSK", ("mitigates",)),
    ("DES", "DES", ("depends_on", "derives_from", "duplicates", "relates_to")),
    ("DES", "STD", ("references",)),
    ("RSK", "REQ", ("impacts", "mitigates", "references")),
    ("RSK", "SPEC", ("impacts", "references")),
    ("RSK", "DES", ("impacts", "references")),
    ("RSK", "TC", ("impacts", "references")),
    ("RSK", "CPT", ("impacts", "references")),
    ("RSK", "PRT", ("impacts", "references")),
    ("RSK", "CHG", ("impacts", "references")),
    ("RSK", "RSK", ("depends_on", "duplicates", "relates_to")),
    ("RSK", "STD", ("references",)),
    ("RSK", "DEF", ("impacts", "references")),
    ("CHG", "REQ", ("impacts", "implements", "blocks", "references")),
    ("CHG", "SPEC", ("impacts", "implements", "blocks", "references")),
    ("CHG", "DES", ("impacts", "implements", "blocks", "references")),
    ("CHG", "TC", ("impacts", "blocks", "references")),
    ("CHG", "CPT", ("impacts", "blocks", "references")),
    ("CHG", "PRT", ("impacts", "blocks", "references")),
    ("CHG", "TS", ("impacts", "blocks", "references")),
    ("CHG", "RSK", ("mitigates", "impacts", "references")),
    ("CHG", "CHG", ("depends_on", "duplicates", "blocks", "relates_to")),
    ("CHG", "STD", ("references",)),
    ("CHG", "DEF", ("implements", "references")),
    ("DEF", "REQ", ("impacts", "references")),
    ("DEF", "SPEC", ("impacts", "references")),
    ("DEF", "TC", ("references",)),
    ("DEF", "CPT", ("references",)),
    ("DEF", "PRT", ("references",)),
    ("DEF", "CHG", ("references",)),
    ("DEF", "RPT", ("references",)),
    ("DEF", "DES", ("impacts", "references")),
    ("DEF", "RSK", ("references",)),
    ("DEF", "DEF", ("duplicates", "relates_to", "depends_on")),
    ("DEF", "STD", ("references",)),
    ("DEF", "CMP", ("references",)),
    ("CMP", "DEF", ("references",)),
)
FROZEN_LINK_KINDS = (
    "REQ",
    "TC",
    "DES",
    "RSK",
    "CHG",
    "CPT",
    "DEF",
    "CMP",
    "TS",
    "SPEC",
    "PRT",
    "RPT",
    "STD",
)
FROZEN_TAG_HOST_KINDS = ("REQ", "DES", "RSK", "CHG", "CPT", "SPEC", "PRT", "RPT", "STD")
FROZEN_LINK_ALIASES = {"TCO": "CPT", "PROT": "PRT"}


def _frozen_link_triples() -> list[dict]:
    """Expand the frozen manual and tag rules into all accepted storage triples."""
    canonical = {
        (source, target, role) for source, target, roles in FROZEN_LINK_RULE_ROWS for role in roles
    }
    canonical.update(
        (source, target, "references")
        for source in FROZEN_TAG_HOST_KINDS
        for target in FROZEN_LINK_KINDS
    )
    triples = set()
    for source, target, role in canonical:
        sources = (
            source,
            *(alias for alias, kind in FROZEN_LINK_ALIASES.items() if kind == source),
        )
        targets = (
            target,
            *(alias for alias, kind in FROZEN_LINK_ALIASES.items() if kind == target),
        )
        triples.update(
            (stored_source, stored_target, role)
            for stored_source in sources
            for stored_target in targets
        )
    return [dict(zip(("source_type", "target_type", "role"), triple)) for triple in sorted(triples)]


def _create_link_rules(bind) -> None:
    """Seed frozen link triples and constrain new links without changing existing rows."""
    table = op.create_table(
        "allowed_link_triples",
        sa.Column("source_type", sa.String(30), primary_key=True),
        sa.Column("target_type", sa.String(30), primary_key=True),
        sa.Column("role", sa.String(50), primary_key=True),
    )
    bind.execute(table.insert(), _frozen_link_triples())
    op.create_foreign_key(
        "fk_artefact_links_allowed_triple",
        "artefact_links",
        "allowed_link_triples",
        ["source_type", "target_type", "role"],
        ["source_type", "target_type", "role"],
        postgresql_not_valid=True,
    )


DOC_TYPE_RESOURCES = (
    "CHG",
    "CMP",
    "CPT",
    "DEF",
    "DES",
    "PRT",
    "REQ",
    "RPT",
    "RSK",
    "SPEC",
    "STD",
    "TC",
    "TS",
)
VISIBILITIES = ("internal", "customer")
DEFAULT_POLICIES = [
    {
        "name": "Requirements",
        "description": "",
        "scope": "document",
        "permissions": {
            "REQ": [
                "approve",
                "comment",
                "create",
                "delete",
                "edit",
                "export",
                "import",
                "review",
                "view",
            ]
        },
        "type_tags": {"REQ": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Specifications",
        "description": "",
        "scope": "document",
        "permissions": {
            "SPEC": ["approve", "comment", "create", "delete", "edit", "import", "review", "view"]
        },
        "type_tags": {"SPEC": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Standards",
        "description": "",
        "scope": "document",
        "permissions": {"STD": ["comment", "create", "delete", "edit", "import", "view"]},
        "type_tags": {"STD": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Designs",
        "description": "",
        "scope": "document",
        "permissions": {
            "DES": ["approve", "comment", "create", "delete", "edit", "review", "view"]
        },
        "type_tags": {"DES": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Risks",
        "description": "",
        "scope": "document",
        "permissions": {"RSK": ["comment", "create", "delete", "edit", "view"]},
        "type_tags": {"RSK": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Change Requests",
        "description": "",
        "scope": "document",
        "permissions": {
            "CHG": ["approve", "comment", "create", "delete", "edit", "review", "view"]
        },
        "type_tags": {"CHG": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Concepts",
        "description": "",
        "scope": "document",
        "permissions": {
            "CPT": ["approve", "comment", "create", "delete", "edit", "review", "view"]
        },
        "type_tags": {"CPT": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Test Cases",
        "description": "",
        "scope": "document",
        "permissions": {
            "TC": [
                "approve",
                "comment",
                "create",
                "delete",
                "edit",
                "export",
                "import",
                "review",
                "view",
            ]
        },
        "type_tags": {"TC": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Suites",
        "description": "",
        "scope": "document",
        "permissions": {"TS": ["approve", "create", "delete", "edit", "plan", "review", "view"]},
        "type_tags": {"TS": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Campaigns",
        "description": "",
        "scope": "document",
        "permissions": {"CMP": ["create", "delete", "edit", "execute", "plan", "view"]},
        "type_tags": {"CMP": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Defects",
        "description": "",
        "scope": "document",
        "permissions": {
            "DEF": ["approve", "comment", "create", "delete", "edit", "review", "view"]
        },
        "type_tags": {"DEF": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Protocols",
        "description": "",
        "scope": "document",
        "permissions": {
            "PRT": ["approve", "comment", "create", "delete", "edit", "import", "review", "view"]
        },
        "type_tags": {"PRT": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Reports",
        "description": "",
        "scope": "document",
        "permissions": {
            "RPT": ["approve", "comment", "create", "delete", "edit", "import", "view"]
        },
        "type_tags": {"RPT": {"all": True, "visibility": [], "tags": []}},
    },
    {
        "name": "Baselines",
        "description": "",
        "scope": "project",
        "permissions": {"baseline": ["create", "delete", "edit", "view"]},
        "type_tags": {},
    },
    {
        "name": "Parameters",
        "description": "",
        "scope": "project",
        "permissions": {"parameter": ["create", "delete", "edit", "view"]},
        "type_tags": {},
    },
    {
        "name": "Traceability",
        "description": "",
        "scope": "project",
        "permissions": {"link": ["create", "delete", "view"]},
        "type_tags": {},
    },
    {
        "name": "Project Management",
        "description": "",
        "scope": "project",
        "permissions": {"project": ["create", "edit", "view"]},
        "type_tags": {},
    },
    {
        "name": "Read Internal",
        "description": "",
        "scope": "project",
        "permissions": {
            "CHG": ["comment", "view"],
            "CMP": ["view"],
            "CPT": ["comment", "view"],
            "DEF": ["comment", "view"],
            "DES": ["comment", "view"],
            "PRT": ["comment", "view"],
            "REQ": ["comment", "view"],
            "RPT": ["comment", "view"],
            "RSK": ["comment", "view"],
            "SPEC": ["comment", "view"],
            "STD": ["comment", "view"],
            "TC": ["comment", "view"],
            "TS": ["view"],
            "baseline": ["view"],
            "parameter": ["view"],
            "link": ["view"],
            "project": ["view"],
        },
        "type_tags": {
            "CHG": {"all": True, "visibility": [], "tags": []},
            "CMP": {"all": True, "visibility": [], "tags": []},
            "CPT": {"all": True, "visibility": [], "tags": []},
            "DEF": {"all": True, "visibility": [], "tags": []},
            "DES": {"all": True, "visibility": [], "tags": []},
            "PRT": {"all": True, "visibility": [], "tags": []},
            "REQ": {"all": True, "visibility": [], "tags": []},
            "RPT": {"all": True, "visibility": [], "tags": []},
            "RSK": {"all": True, "visibility": [], "tags": []},
            "SPEC": {"all": True, "visibility": [], "tags": []},
            "STD": {"all": True, "visibility": [], "tags": []},
            "TC": {"all": True, "visibility": [], "tags": []},
            "TS": {"all": True, "visibility": [], "tags": []},
        },
    },
    {
        "name": "Read Customer",
        "description": "",
        "scope": "project",
        "permissions": {
            "CHG": ["comment", "view"],
            "CMP": ["view"],
            "CPT": ["comment", "view"],
            "DEF": ["comment", "view"],
            "DES": ["comment", "view"],
            "PRT": ["comment", "view"],
            "REQ": ["comment", "view"],
            "RPT": ["comment", "view"],
            "RSK": ["comment", "view"],
            "SPEC": ["comment", "view"],
            "STD": ["comment", "view"],
            "TC": ["comment", "view"],
            "TS": ["view"],
            "baseline": ["view"],
            "parameter": ["view"],
            "link": ["view"],
            "project": ["view"],
        },
        "type_tags": {
            "CHG": {"all": False, "visibility": ["customer"], "tags": []},
            "CMP": {"all": False, "visibility": ["customer"], "tags": []},
            "CPT": {"all": False, "visibility": ["customer"], "tags": []},
            "DEF": {"all": False, "visibility": ["customer"], "tags": []},
            "DES": {"all": False, "visibility": ["customer"], "tags": []},
            "PRT": {"all": False, "visibility": ["customer"], "tags": []},
            "REQ": {"all": False, "visibility": ["customer"], "tags": []},
            "RPT": {"all": False, "visibility": ["customer"], "tags": []},
            "RSK": {"all": False, "visibility": ["customer"], "tags": []},
            "SPEC": {"all": False, "visibility": ["customer"], "tags": []},
            "STD": {"all": False, "visibility": ["customer"], "tags": []},
            "TC": {"all": False, "visibility": ["customer"], "tags": []},
            "TS": {"all": False, "visibility": ["customer"], "tags": []},
        },
    },
    {
        "name": "Review Internal",
        "description": "",
        "scope": "project",
        "permissions": {
            "CHG": ["review"],
            "CMP": ["review"],
            "CPT": ["review"],
            "DEF": ["review"],
            "DES": ["review"],
            "PRT": ["review"],
            "REQ": ["review"],
            "RPT": ["review"],
            "RSK": ["review"],
            "SPEC": ["review"],
            "STD": ["review"],
            "TC": ["review"],
            "TS": ["review"],
        },
        "type_tags": {
            "CHG": {"all": True, "visibility": [], "tags": []},
            "CMP": {"all": True, "visibility": [], "tags": []},
            "CPT": {"all": True, "visibility": [], "tags": []},
            "DEF": {"all": True, "visibility": [], "tags": []},
            "DES": {"all": True, "visibility": [], "tags": []},
            "PRT": {"all": True, "visibility": [], "tags": []},
            "REQ": {"all": True, "visibility": [], "tags": []},
            "RPT": {"all": True, "visibility": [], "tags": []},
            "RSK": {"all": True, "visibility": [], "tags": []},
            "SPEC": {"all": True, "visibility": [], "tags": []},
            "STD": {"all": True, "visibility": [], "tags": []},
            "TC": {"all": True, "visibility": [], "tags": []},
            "TS": {"all": True, "visibility": [], "tags": []},
        },
    },
    {
        "name": "Review Customer",
        "description": "",
        "scope": "project",
        "permissions": {
            "CHG": ["review"],
            "CMP": ["review"],
            "CPT": ["review"],
            "DEF": ["review"],
            "DES": ["review"],
            "PRT": ["review"],
            "REQ": ["review"],
            "RPT": ["review"],
            "RSK": ["review"],
            "SPEC": ["review"],
            "STD": ["review"],
            "TC": ["review"],
            "TS": ["review"],
        },
        "type_tags": {
            "CHG": {"all": False, "visibility": ["customer"], "tags": []},
            "CMP": {"all": False, "visibility": ["customer"], "tags": []},
            "CPT": {"all": False, "visibility": ["customer"], "tags": []},
            "DEF": {"all": False, "visibility": ["customer"], "tags": []},
            "DES": {"all": False, "visibility": ["customer"], "tags": []},
            "PRT": {"all": False, "visibility": ["customer"], "tags": []},
            "REQ": {"all": False, "visibility": ["customer"], "tags": []},
            "RPT": {"all": False, "visibility": ["customer"], "tags": []},
            "RSK": {"all": False, "visibility": ["customer"], "tags": []},
            "SPEC": {"all": False, "visibility": ["customer"], "tags": []},
            "STD": {"all": False, "visibility": ["customer"], "tags": []},
            "TC": {"all": False, "visibility": ["customer"], "tags": []},
            "TS": {"all": False, "visibility": ["customer"], "tags": []},
        },
    },
    {
        "name": "Access Management",
        "description": "",
        "scope": "app",
        "permissions": {"access": ["create", "delete", "edit", "view"]},
        "type_tags": {},
    },
    {
        "name": "Application Administration",
        "description": "",
        "scope": "app",
        "permissions": {
            "CHG": ["approve", "comment", "create", "delete", "edit", "review", "view"],
            "CMP": ["create", "delete", "edit", "execute", "plan", "review", "view"],
            "CPT": ["approve", "comment", "create", "delete", "edit", "review", "view"],
            "DEF": ["approve", "comment", "create", "delete", "edit", "review", "view"],
            "DES": ["approve", "comment", "create", "delete", "edit", "review", "view"],
            "PRT": ["approve", "comment", "create", "delete", "edit", "import", "review", "view"],
            "REQ": [
                "approve",
                "comment",
                "create",
                "delete",
                "edit",
                "export",
                "import",
                "review",
                "view",
            ],
            "RPT": ["approve", "comment", "create", "delete", "edit", "import", "review", "view"],
            "RSK": ["comment", "create", "delete", "edit", "review", "view"],
            "SPEC": ["approve", "comment", "create", "delete", "edit", "import", "review", "view"],
            "STD": ["comment", "create", "delete", "edit", "import", "review", "view"],
            "TC": [
                "approve",
                "comment",
                "create",
                "delete",
                "edit",
                "export",
                "import",
                "review",
                "view",
            ],
            "TS": ["approve", "create", "delete", "edit", "plan", "review", "view"],
            "baseline": ["create", "delete", "edit", "view"],
            "parameter": ["create", "delete", "edit", "view"],
            "link": ["create", "delete", "view"],
            "project": ["create", "edit", "view"],
            "users": ["create", "delete", "edit", "view"],
            "access": ["create", "delete", "edit", "view"],
            "application": ["create", "delete", "edit", "view"],
        },
        "type_tags": {
            "CHG": {"all": True, "visibility": [], "tags": []},
            "CMP": {"all": True, "visibility": [], "tags": []},
            "CPT": {"all": True, "visibility": [], "tags": []},
            "DEF": {"all": True, "visibility": [], "tags": []},
            "DES": {"all": True, "visibility": [], "tags": []},
            "PRT": {"all": True, "visibility": [], "tags": []},
            "REQ": {"all": True, "visibility": [], "tags": []},
            "RPT": {"all": True, "visibility": [], "tags": []},
            "RSK": {"all": True, "visibility": [], "tags": []},
            "SPEC": {"all": True, "visibility": [], "tags": []},
            "STD": {"all": True, "visibility": [], "tags": []},
            "TC": {"all": True, "visibility": [], "tags": []},
            "TS": {"all": True, "visibility": [], "tags": []},
        },
    },
]

DEFAULT_GROUPS = [
    {
        "name": "Customers",
        "description": "",
        "policy_names": ["Read Customer"],
    },
    {
        "name": "Product Owners",
        "description": "",
        "policy_names": [
            "Read Internal",
            "Read Customer",
            "Requirements",
            "Specifications",
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
            "Read Internal",
            "Read Customer",
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
            "Read Internal",
            "Read Customer",
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

ARTEFACT_TABLES = (
    "requirements",
    "test_cases",
    "documents",
    "test_suites",
    "test_campaigns",
    "design_items",
    "risk_items",
    "change_requests",
    "test_concepts",
    "defects",
)

policies = sa.table(
    "policies",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("scope", sa.String),
    sa.column("permissions", sa.JSON),
    sa.column("type_tags", sa.JSON),
    sa.column("is_default", sa.Boolean),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)
groups = sa.table(
    "groups",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)
group_policies = sa.table(
    "group_policies",
    sa.column("group_id", sa.Integer),
    sa.column("policy_id", sa.Integer),
)
memberships = sa.table(
    "project_memberships",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.Integer),
    sa.column("project_id", sa.Integer),
    sa.column("role", sa.String),
)
external_types = sa.table(
    "project_external_doc_types",
    sa.column("membership_id", sa.Integer),
    sa.column("doc_type", sa.String),
)
users = sa.table("users", sa.column("id", sa.Integer), sa.column("role", sa.String))
access = sa.table(
    "project_access",
    sa.column("id", sa.Integer),
    sa.column("project_id", sa.Integer),
    sa.column("user_id", sa.Integer),
    sa.column("owner", sa.Boolean),
    sa.column("created_at", sa.DateTime),
)
access_policies = sa.table(
    "project_access_policies",
    sa.column("access_id", sa.Integer),
    sa.column("policy_id", sa.Integer),
)


def _insert_policy(
    bind,
    name: str,
    permissions: dict,
    type_tags: dict,
    default: bool,
    *,
    scope: str = "project",
    description: str = "",
) -> int:
    """Insert a policy and return its id."""
    now = datetime.utcnow()
    bind.execute(
        policies.insert().values(
            name=name,
            description=description,
            scope=scope,
            permissions=permissions,
            type_tags=type_tags,
            is_default=default,
            created_at=now,
            updated_at=now,
        )
    )
    return bind.execute(sa.select(policies.c.id).where(policies.c.name == name)).scalar()


def _type_tags(permissions: dict, visibility: list) -> dict:
    """The visibility tags on every document type the matrix grants actions on."""
    return {
        doc_type: {"visibility": list(visibility), "tags": []}
        for doc_type in DOC_TYPE_RESOURCES
        if permissions.get(doc_type)
    }


def _create_tables() -> None:
    """Create the policy, group, tag and access tables and the creator columns."""
    for table in ARTEFACT_TABLES:
        op.add_column(
            table,
            sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        )
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("permissions", sa.JSON, nullable=False),
        sa.Column("type_tags", sa.JSON, nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "group_policies",
        sa.Column(
            "group_id",
            sa.Integer,
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("policy_id", sa.Integer, sa.ForeignKey("policies.id"), primary_key=True),
    )
    op.create_table(
        "group_memberships",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_membership_group_user"),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "artefact_tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tag_id", sa.Integer, sa.ForeignKey("tags.id"), nullable=False),
        sa.Column("artefact_type", sa.String(30), nullable=False),
        sa.Column("artefact_id", sa.Integer, nullable=False),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("tag_id", "artefact_type", "artefact_id", name="uq_artefact_tag"),
    )
    op.create_index("ix_artefact_tags_artefact", "artefact_tags", ["artefact_type", "artefact_id"])
    op.create_index("ix_artefact_tags_tag_id", "artefact_tags", ["tag_id"])
    op.create_index("ix_artefact_tags_project_id", "artefact_tags", ["project_id"])
    op.create_table(
        "project_access",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("owner", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("policy_group_id", sa.Integer, sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("inherit_policies", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.CheckConstraint(
            "(user_id IS NULL) <> (group_id IS NULL)",
            name="ck_project_access_one_principal",
        ),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_access_project_user"),
        sa.UniqueConstraint("project_id", "group_id", name="uq_project_access_project_group"),
    )
    op.create_index("ix_project_access_project_id", "project_access", ["project_id"])
    op.create_index("ix_project_access_user_id", "project_access", ["user_id"])
    op.create_index("ix_project_access_group_id", "project_access", ["group_id"])
    op.create_table(
        "project_access_policies",
        sa.Column(
            "access_id",
            sa.Integer,
            sa.ForeignKey("project_access.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("policy_id", sa.Integer, sa.ForeignKey("policies.id"), primary_key=True),
    )

    op.create_table(
        "user_application_policies",
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("policy_id", sa.Integer, sa.ForeignKey("policies.id"), primary_key=True),
    )


def _validate_catalogue() -> None:
    """Validate frozen catalogue names, scopes and group policy references."""
    names = [spec["name"] for spec in DEFAULT_POLICIES]
    group_names = [spec["name"] for spec in DEFAULT_GROUPS]
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate policy name in release catalogue")
    if len(group_names) != len(set(group_names)):
        raise RuntimeError("Duplicate group name in release catalogue")
    for spec in DEFAULT_POLICIES:
        if spec["scope"] not in {"document", "project", "app"}:
            raise RuntimeError(f"Unknown policy scope: {spec['scope']}")
        if not isinstance(spec["permissions"], dict) or not isinstance(spec["type_tags"], dict):
            raise RuntimeError(f"Invalid frozen policy rules: {spec['name']}")
    for spec in DEFAULT_GROUPS:
        chosen = spec["policy_names"]
        if len(chosen) != len(set(chosen)):
            raise RuntimeError(f"Duplicate group policy: {spec['name']}")
        missing = set(chosen) - set(names)
        if missing:
            raise RuntimeError(f"Unknown policy in group {spec['name']}: {sorted(missing)}")


def _seed(bind) -> dict:
    """Insert frozen scoped policies, groups and owned policy associations."""
    _validate_catalogue()
    ids = {
        spec["name"]: _insert_policy(
            bind,
            spec["name"],
            spec["permissions"],
            spec["type_tags"],
            True,
            scope=spec["scope"],
            description=spec["description"],
        )
        for spec in DEFAULT_POLICIES
    }
    now = datetime.utcnow()
    for spec in DEFAULT_GROUPS:
        bind.execute(
            groups.insert().values(
                name=spec["name"],
                description=spec["description"],
                created_at=now,
                updated_at=now,
            )
        )
        group_id = bind.execute(
            sa.select(groups.c.id).where(groups.c.name == spec["name"])
        ).scalar_one()
        for name in spec["policy_names"]:
            bind.execute(group_policies.insert().values(group_id=group_id, policy_id=ids[name]))
    return ids


def _convert_memberships(bind, ids: dict) -> None:
    """Preserve released membership rights with scoped defaults and tailored readers."""
    read_matrix = {
        resource: actions
        for spec in DEFAULT_POLICIES
        if spec["name"] == "Read Internal"
        for resource, actions in spec["permissions"].items()
        if resource != "parameter"
    }
    full_policy_names = [
        spec["name"]
        for spec in DEFAULT_POLICIES
        if spec["scope"] in {"document", "project"}
        and spec["name"]
        not in {"Read Internal", "Read Customer", "Review Internal", "Review Customer"}
    ]
    types_by_membership: dict = {}
    for membership_id, doc_type in bind.execute(
        sa.select(external_types.c.membership_id, external_types.c.doc_type)
    ).all():
        types_by_membership.setdefault(membership_id, set()).add(doc_type)
    for membership in bind.execute(
        sa.select(
            memberships.c.id,
            memberships.c.user_id,
            memberships.c.project_id,
            memberships.c.role,
            users.c.role.label("user_role"),
        ).join(users, users.c.id == memberships.c.user_id)
    ).all():
        user_role = str(membership.user_role).split(".")[-1]
        membership_role = str(membership.role).split(".")[-1]
        if user_role == "admin":
            continue
        if user_role == "maintainer" and membership_role == "maintainer":
            selected = [ids[name] for name in full_policy_names]
        else:
            if user_role == "maintainer":
                chosen = set(DOC_TYPE_RESOURCES)
                visibility = list(VISIBILITIES)
                name = "Released Read-only"
            else:
                chosen = types_by_membership.get(membership.id, set()) & set(DOC_TYPE_RESOURCES)
                visibility = ["customer"]
                label = (
                    "all document types"
                    if chosen == set(DOC_TYPE_RESOURCES)
                    else ", ".join(sorted(chosen)) or "no document types"
                )
                name = f"Released Read ({label})"
            if name not in ids:
                matrix = {
                    resource: actions
                    for resource, actions in read_matrix.items()
                    if resource not in DOC_TYPE_RESOURCES or resource in chosen
                }
                ids[name] = _insert_policy(
                    bind,
                    name,
                    matrix,
                    _type_tags(matrix, visibility),
                    False,
                    description="Preserves released read-only membership permissions and origins.",
                )
            selected = [ids[name]]
        bind.execute(
            access.insert().values(
                project_id=membership.project_id,
                user_id=membership.user_id,
                owner=False,
                created_at=datetime.utcnow(),
            )
        )
        entry = bind.execute(
            sa.select(access.c.id).where(
                access.c.project_id == membership.project_id,
                access.c.user_id == membership.user_id,
            )
        ).scalar_one()
        for policy in selected:
            bind.execute(access_policies.insert().values(access_id=entry, policy_id=policy))


def _link_existing_activity(bind) -> None:
    """Assign existing activity to the configured seed administrator."""
    from app.core.config import settings

    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("email", sa.String),
        sa.column("role", sa.String),
    )
    activities = sa.table("artefact_activities", sa.column("actor_user_id", sa.Integer))
    admin_id = bind.execute(
        sa.select(users.c.id).where(
            users.c.email == settings.ADMIN_EMAIL, sa.cast(users.c.role, sa.String) == "admin"
        )
    ).scalar_one_or_none()
    if admin_id is not None:
        bind.execute(
            activities.update()
            .where(activities.c.actor_user_id.is_(None))
            .values(actor_user_id=admin_id)
        )


def _workflow_actor(name: str) -> sa.Column:
    """Create a nullable workflow actor reference with existing user-deletion semantics."""
    return sa.Column(
        name, sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


def _create_workflow_tables() -> None:
    """Create workflow cycles, requests and archives without changing existing artefacts."""
    op.create_table(
        "artefact_workflows",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer,
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("artefact_type", sa.String(30), nullable=False),
        sa.Column("artefact_id", sa.Integer, nullable=False),
        sa.Column("revision_number", sa.Integer, nullable=False),
        _workflow_actor("revision_creator_id"),
        sa.Column("phase", sa.String(20), nullable=False),
        sa.Column(
            "authorizing_change_id",
            sa.Integer,
            sa.ForeignKey("change_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _workflow_actor("reviewer_id"),
        _workflow_actor("approver_id"),
        sa.Column("review_content_hash", sa.String(64), nullable=True),
        _workflow_actor("reviewed_by_id"),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        _workflow_actor("approved_by_id"),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("artefact_type", "artefact_id", name="uq_artefact_workflow"),
        sa.CheckConstraint(
            "phase IN ('Draft', 'Review', 'Approval', 'Approved')",
            name="ck_artefact_workflow_phase",
        ),
    )
    op.create_table(
        "artefact_revisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "workflow_id", sa.Integer, sa.ForeignKey("artefact_workflows.id"), nullable=False
        ),
        sa.Column("revision_number", sa.Integer, nullable=False),
        sa.Column("content_snapshot", sa.JSON, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "authorizing_change_id",
            sa.Integer,
            sa.ForeignKey("change_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _workflow_actor("reviewer_id"),
        _workflow_actor("approver_id"),
        _workflow_actor("reviewed_by_id"),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        _workflow_actor("approved_by_id"),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("captured_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("workflow_id", "revision_number", name="uq_artefact_revision"),
    )
    op.create_table(
        "artefact_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "workflow_id", sa.Integer, sa.ForeignKey("artefact_workflows.id"), nullable=False
        ),
        sa.Column("revision_number", sa.Integer, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column(
            "requester_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        _workflow_actor("decided_by_id"),
        sa.Column("decided_at", sa.DateTime, nullable=True),
        sa.CheckConstraint("kind IN ('review', 'approval')", name="ck_artefact_request_kind"),
        sa.CheckConstraint(
            "status IN ('pending', 'answered', 'declined', 'superseded')",
            name="ck_artefact_request_status",
        ),
    )
    op.create_index(
        "uq_artefact_requests_pending_cycle",
        "artefact_requests",
        ["workflow_id", "revision_number", "kind"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "artefact_request_recipients",
        sa.Column(
            "request_id",
            sa.Integer,
            sa.ForeignKey("artefact_requests.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    op.create_table(
        "artefact_revision_files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "revision_id", sa.Integer, sa.ForeignKey("artefact_revisions.id"), nullable=False
        ),
        sa.Column("attachment_id", sa.Integer, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("source_ref", sa.String(200), nullable=True),
        _workflow_actor("uploaded_by_id"),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )
    op.add_column("artefact_comments", sa.Column("revision_number", sa.Integer, nullable=True))
    op.add_column("artefact_comments", sa.Column("content_hash", sa.String(64), nullable=True))
    op.add_column("artefact_comments", sa.Column("review_request_id", sa.Integer, nullable=True))
    op.create_foreign_key(
        "fk_artefact_comments_review_request",
        "artefact_comments",
        "artefact_requests",
        ["review_request_id"],
        ["id"],
        ondelete="SET NULL",
    )


def upgrade() -> None:
    """Add creators, profile pictures, policies, groups, tags and access entries; seed defaults; convert
    the 1.1.0 memberships."""
    _create_tables()
    bind = op.get_bind()
    _convert_memberships(bind, _seed(bind))
    op.add_column("users", sa.Column("profile_picture", sa.LargeBinary(), nullable=True))
    op.add_column("artefact_comments", sa.Column("author_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_artefact_comments_author_user",
        "artefact_comments",
        "users",
        ["author_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    for table in ("artefact_activities", "notifications"):
        op.add_column(table, sa.Column("actor_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_actor_user", table, "users", ["actor_user_id"], ["id"], ondelete="SET NULL"
        )
    _link_existing_activity(bind)
    _create_link_rules(bind)
    _create_workflow_tables()


def downgrade() -> None:
    """Drop the access entries, tags, groups, policies, creator and profile-picture columns."""
    op.drop_constraint(
        "fk_artefact_comments_review_request", "artefact_comments", type_="foreignkey"
    )
    op.drop_column("artefact_comments", "review_request_id")
    op.drop_column("artefact_comments", "content_hash")
    op.drop_column("artefact_comments", "revision_number")
    op.drop_table("artefact_revision_files")
    op.drop_table("artefact_request_recipients")
    op.drop_index("uq_artefact_requests_pending_cycle", table_name="artefact_requests")
    op.drop_table("artefact_requests")
    op.drop_table("artefact_revisions")
    op.drop_table("artefact_workflows")
    op.drop_constraint("fk_artefact_links_allowed_triple", "artefact_links", type_="foreignkey")
    op.drop_table("allowed_link_triples")
    for table in ("notifications", "artefact_activities"):
        op.drop_constraint(f"fk_{table}_actor_user", table, type_="foreignkey")
        op.drop_column(table, "actor_user_id")
    op.drop_constraint("fk_artefact_comments_author_user", "artefact_comments", type_="foreignkey")
    op.drop_column("artefact_comments", "author_user_id")
    op.drop_column("users", "profile_picture")
    op.drop_table("user_application_policies")
    op.drop_table("project_access_policies")
    op.drop_index("ix_project_access_group_id", table_name="project_access")
    op.drop_index("ix_project_access_user_id", table_name="project_access")
    op.drop_index("ix_project_access_project_id", table_name="project_access")
    op.drop_table("project_access")
    op.drop_index("ix_artefact_tags_project_id", table_name="artefact_tags")
    op.drop_index("ix_artefact_tags_tag_id", table_name="artefact_tags")
    op.drop_index("ix_artefact_tags_artefact", table_name="artefact_tags")
    op.drop_table("artefact_tags")
    op.drop_table("tags")
    op.drop_table("group_memberships")
    op.drop_table("group_policies")
    op.drop_table("groups")
    op.drop_table("policies")
    for table in ARTEFACT_TABLES:
        op.drop_column(table, "created_by_id")
