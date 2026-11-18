"""defect managers group

Revision ID: d4e6f8a1c3b5
Revises: b8e3d1f6a920
Create Date: 2026-11-18

Adds the default Defect Managers group, holding the built-in Read Internal, Read Customer and
Defects policies, given per project like Product Owners. Its members on a project receive the
email of a failed Jira send of that project. Downgrade removes the group
while no project access names it.
"""

from datetime import datetime, timezone

import sqlalchemy as sa

from alembic import op

revision = "d4e6f8a1c3b5"
down_revision = "b8e3d1f6a920"
branch_labels = None
depends_on = None

DEFECT_MANAGERS = "Defect Managers"
POLICY_NAMES = ("Read Internal", "Read Customer", "Defects")

policies = sa.table(
    "policies",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("is_default", sa.Boolean),
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
project_access = sa.table(
    "project_access",
    sa.column("policy_group_id", sa.Integer),
)


def upgrade() -> None:
    """Add the Defect Managers group with its three built-in policies when it is missing."""
    bind = op.get_bind()
    if bind.execute(sa.select(groups.c.id).where(groups.c.name == DEFECT_MANAGERS)).scalar():
        return
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    bind.execute(
        groups.insert().values(name=DEFECT_MANAGERS, description="", created_at=now, updated_at=now)
    )
    group_id = bind.execute(
        sa.select(groups.c.id).where(groups.c.name == DEFECT_MANAGERS)
    ).scalar_one()
    policy_ids = (
        bind.execute(
            sa.select(policies.c.id).where(
                policies.c.name.in_(POLICY_NAMES), policies.c.is_default.is_(True)
            )
        )
        .scalars()
        .all()
    )
    if policy_ids:
        bind.execute(
            group_policies.insert(),
            [{"group_id": group_id, "policy_id": policy_id} for policy_id in policy_ids],
        )


def downgrade() -> None:
    """Remove the Defect Managers group while no project access names it."""
    bind = op.get_bind()
    group_id = bind.execute(sa.select(groups.c.id).where(groups.c.name == DEFECT_MANAGERS)).scalar()
    if group_id is None:
        return
    used = bind.execute(
        sa.select(sa.func.count())
        .select_from(project_access)
        .where(project_access.c.policy_group_id == group_id)
    ).scalar_one()
    if used:
        raise RuntimeError(
            f"Cannot downgrade below d4e6f8a1c3b5: {used} project accesses use Defect Managers."
        )
    bind.execute(group_policies.delete().where(group_policies.c.group_id == group_id))
    bind.execute(groups.delete().where(groups.c.id == group_id))
