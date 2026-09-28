"""policies without project member management

Removes the member resource and the manage action from every stored policy permission
matrix, and the words on project members from the description of the default Project
Administrator. Downgrade gives the default Project Administrator member view and manage
again and restores its description.

Revision ID: 449b8eddaf9e
Revises: fda71a60c062
Create Date: 2026-09-28

"""

import sqlalchemy as sa

from alembic import op

revision = "449b8eddaf9e"
down_revision = "fda71a60c062"
branch_labels = None
depends_on = None

MEMBER = "member"
MANAGE = "manage"
ADMINISTRATOR = "Project Administrator"
OLD_DESCRIPTION = "Manage project members, campaigns and baselines; review and approve change requests and risks; review requirements; export requirements and test cases."
NEW_DESCRIPTION = "Manage campaigns and baselines; review and approve change requests and risks; review requirements; export requirements and test cases."

policies = sa.table(
    "policies",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("permissions", sa.JSON),
    sa.column("is_default", sa.Boolean),
)


def without_member_management(matrix: dict) -> dict:
    """The matrix without the member resource and without the manage action."""
    return {
        key: [action for action in (actions or []) if action != MANAGE]
        for key, actions in (matrix or {}).items()
        if key != MEMBER
    }


def with_member_management(matrix: dict) -> dict:
    """The matrix with member view and manage added."""
    return {**(matrix or {}), MEMBER: [MANAGE, "view"]}


def _default_administrator():
    """The condition selecting the default Project Administrator policy."""
    return sa.and_(policies.c.is_default.is_(True), policies.c.name == ADMINISTRATOR)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(policies.c.id, policies.c.permissions)).all()
    for row in rows:
        cleaned = without_member_management(row.permissions or {})
        if cleaned != (row.permissions or {}):
            bind.execute(
                policies.update().where(policies.c.id == row.id).values(permissions=cleaned)
            )
    bind.execute(
        policies.update()
        .where(_default_administrator(), policies.c.description == OLD_DESCRIPTION)
        .values(description=NEW_DESCRIPTION)
    )


def downgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(
        sa.select(policies.c.id, policies.c.permissions).where(_default_administrator())
    ).first()
    if row is None:
        return
    bind.execute(
        policies.update()
        .where(policies.c.id == row.id)
        .values(permissions=with_member_management(row.permissions))
    )
    bind.execute(
        policies.update()
        .where(policies.c.id == row.id, policies.c.description == NEW_DESCRIPTION)
        .values(description=OLD_DESCRIPTION)
    )
