"""visions

Revision ID: 637f976e78e0
Revises: d1f6b8a3e572
Create Date: 2026-10-27

Adds the VIS document kind to access and links: the allowed VIS link triples, the built-in
Visions policy, a VIS entry equal to the SPEC entry in the built-in Read, Review and
Application Administration policies, and Visions in the Product Owners group and in every
access entry holding the released maintainer policy set. Downgrade removes them while no
vision and no VIS link exist.
"""

from datetime import datetime, timezone

import sqlalchemy as sa

from alembic import op

revision = "637f976e78e0"
down_revision = "d1f6b8a3e572"
branch_labels = None
depends_on = None

VISIONS = "Visions"
VIS_ACTIONS = ["approve", "comment", "create", "delete", "edit", "import", "review", "view"]
COVERED_POLICIES = (
    "Read Internal",
    "Read Customer",
    "Review Internal",
    "Review Customer",
    "Application Administration",
)
PRODUCT_OWNERS = "Product Owners"
RELEASED_MAINTAINER_SET = (
    "Requirements",
    "Specifications",
    "Standards",
    "Designs",
    "Risks",
    "Change Requests",
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
    "Project Management",
)
VIS_TRIPLES = (
    ("CHG", "VIS", "blocks"),
    ("CHG", "VIS", "impacts"),
    ("CHG", "VIS", "implements"),
    ("CHG", "VIS", "references"),
    ("CPT", "VIS", "references"),
    ("DES", "VIS", "references"),
    ("PROT", "VIS", "references"),
    ("PRT", "VIS", "references"),
    ("REQ", "VIS", "derives_from"),
    ("REQ", "VIS", "references"),
    ("REQ", "VIS", "refines"),
    ("RPT", "VIS", "references"),
    ("RSK", "VIS", "impacts"),
    ("RSK", "VIS", "references"),
    ("SPEC", "VIS", "derives_from"),
    ("SPEC", "VIS", "references"),
    ("SPEC", "VIS", "refines"),
    ("STD", "VIS", "references"),
    ("TCO", "VIS", "references"),
    ("VIS", "CHG", "references"),
    ("VIS", "CMP", "references"),
    ("VIS", "CPT", "references"),
    ("VIS", "DEF", "references"),
    ("VIS", "DES", "references"),
    ("VIS", "PROT", "references"),
    ("VIS", "PRT", "references"),
    ("VIS", "REQ", "references"),
    ("VIS", "RPT", "references"),
    ("VIS", "RSK", "references"),
    ("VIS", "SPEC", "references"),
    ("VIS", "STD", "references"),
    ("VIS", "TC", "references"),
    ("VIS", "TCO", "references"),
    ("VIS", "TS", "references"),
    ("VIS", "VIS", "references"),
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
groups = sa.table("groups", sa.column("id", sa.Integer), sa.column("name", sa.String))
group_policies = sa.table(
    "group_policies",
    sa.column("group_id", sa.Integer),
    sa.column("policy_id", sa.Integer),
)
access_policies = sa.table(
    "project_access_policies",
    sa.column("access_id", sa.Integer),
    sa.column("policy_id", sa.Integer),
)
triples = sa.table(
    "allowed_link_triples",
    sa.column("source_type", sa.String),
    sa.column("target_type", sa.String),
    sa.column("role", sa.String),
)
documents = sa.table("documents", sa.column("doc_type", sa.String))
links = sa.table(
    "artefact_links",
    sa.column("source_type", sa.String),
    sa.column("target_type", sa.String),
)


def _now() -> datetime:
    """The current UTC time without a zone, as the access tables store it."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _default_policy_ids(bind, names) -> dict:
    """Ids of the built-in policies with the given names."""
    rows = bind.execute(
        sa.select(policies.c.name, policies.c.id).where(
            policies.c.name.in_(list(names)), policies.c.is_default.is_(True)
        )
    ).all()
    return {name: policy_id for name, policy_id in rows}


def _set_vis_entry(bind, policy_id: int, copy_spec: bool) -> None:
    """Give a built-in policy a VIS entry equal to its SPEC entry, or remove its VIS entry."""
    row = bind.execute(
        sa.select(policies.c.permissions, policies.c.type_tags).where(policies.c.id == policy_id)
    ).one()
    permissions = dict(row.permissions or {})
    type_tags = dict(row.type_tags or {})
    if copy_spec:
        if "SPEC" in permissions:
            permissions["VIS"] = list(permissions["SPEC"])
        if "SPEC" in type_tags:
            type_tags["VIS"] = dict(type_tags["SPEC"])
    else:
        permissions.pop("VIS", None)
        type_tags.pop("VIS", None)
    bind.execute(
        policies.update()
        .where(policies.c.id == policy_id)
        .values(permissions=permissions, type_tags=type_tags, updated_at=_now())
    )


def _released_maintainer_entries(bind, set_ids: list) -> list:
    """Access entries holding every policy of the released maintainer set."""
    rows = bind.execute(
        sa.select(access_policies.c.access_id)
        .where(access_policies.c.policy_id.in_(set_ids))
        .group_by(access_policies.c.access_id)
        .having(sa.func.count(sa.distinct(access_policies.c.policy_id)) == len(set_ids))
    ).all()
    return [row.access_id for row in rows]


def upgrade() -> None:
    """Add the VIS link triples, the Visions policy and its holders."""
    bind = op.get_bind()
    existing = set(
        bind.execute(
            sa.select(triples.c.source_type, triples.c.target_type, triples.c.role)
        ).all()
    )
    new_triples = [
        {"source_type": source, "target_type": target, "role": role}
        for source, target, role in VIS_TRIPLES
        if (source, target, role) not in existing
    ]
    if new_triples:
        bind.execute(triples.insert(), new_triples)
    now = _now()
    bind.execute(
        policies.insert().values(
            name=VISIONS,
            description="",
            scope="document",
            permissions={"VIS": VIS_ACTIONS},
            type_tags={"VIS": {"all": True, "visibility": [], "tags": []}},
            is_default=True,
            created_at=now,
            updated_at=now,
        )
    )
    visions_id = bind.execute(
        sa.select(policies.c.id).where(policies.c.name == VISIONS)
    ).scalar_one()
    for policy_id in _default_policy_ids(bind, COVERED_POLICIES).values():
        _set_vis_entry(bind, policy_id, True)
    owners = bind.execute(sa.select(groups.c.id).where(groups.c.name == PRODUCT_OWNERS)).scalar()
    if owners is not None:
        bind.execute(group_policies.insert().values(group_id=owners, policy_id=visions_id))
    set_ids = list(_default_policy_ids(bind, RELEASED_MAINTAINER_SET).values())
    if len(set_ids) == len(RELEASED_MAINTAINER_SET):
        entries = _released_maintainer_entries(bind, set_ids)
        if entries:
            bind.execute(
                access_policies.insert(),
                [{"access_id": entry, "policy_id": visions_id} for entry in entries],
            )


def downgrade() -> None:
    """Remove the Visions policy, the VIS entries and triples while no vision or VIS link exists."""
    bind = op.get_bind()
    visions = bind.execute(
        sa.select(sa.func.count()).select_from(documents).where(documents.c.doc_type == "VIS")
    ).scalar_one()
    vis_links = bind.execute(
        sa.select(sa.func.count())
        .select_from(links)
        .where(sa.or_(links.c.source_type == "VIS", links.c.target_type == "VIS"))
    ).scalar_one()
    if visions or vis_links:
        raise RuntimeError(
            f"Cannot downgrade below 637f976e78e0: {visions} visions and {vis_links} "
            "links with a vision end exist."
        )
    visions_id = bind.execute(
        sa.select(policies.c.id).where(
            policies.c.name == VISIONS, policies.c.is_default.is_(True)
        )
    ).scalar()
    if visions_id is not None:
        bind.execute(group_policies.delete().where(group_policies.c.policy_id == visions_id))
        bind.execute(access_policies.delete().where(access_policies.c.policy_id == visions_id))
        bind.execute(policies.delete().where(policies.c.id == visions_id))
    for policy_id in _default_policy_ids(bind, COVERED_POLICIES).values():
        _set_vis_entry(bind, policy_id, False)
    for source, target, role in VIS_TRIPLES:
        bind.execute(
            triples.delete().where(
                triples.c.source_type == source,
                triples.c.target_type == target,
                triples.c.role == role,
            )
        )
