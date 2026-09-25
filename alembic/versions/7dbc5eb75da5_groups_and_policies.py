"""groups_and_policies

Revision ID: 7dbc5eb75da5
Revises: f3c17b0a55de
Create Date: 2026-09-22 14:17:38.907970

"""

from datetime import datetime

import sqlalchemy as sa

from alembic import op

revision = "7dbc5eb75da5"
down_revision = "f3c17b0a55de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("base_role", sa.String(length=20), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("doc_tag_scope", sa.JSON(), nullable=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("policy_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["policy_id"], ["policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "group_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_membership_group_user"),
    )
    op.create_table(
        "group_project_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "project_id", name="uq_group_project_grant"),
    )
    _seed_default_policies()


def _seed_default_policies() -> None:
    """Insert the shipped default policies (the personas). Their definitions live in
    app.core.policy_seed, the single source for the personas."""
    from app.core.policy_seed import DEFAULT_POLICIES

    policies = sa.table(
        "policies",
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("base_role", sa.String),
        sa.column("permissions", sa.JSON),
        sa.column("doc_tag_scope", sa.JSON),
        sa.column("is_default", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.utcnow()
    op.bulk_insert(
        policies,
        [
            {
                "name": spec["name"],
                "description": spec["description"],
                "base_role": spec["base_role"],
                "permissions": spec["permissions"],
                "doc_tag_scope": spec.get("doc_tag_scope"),
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            }
            for spec in DEFAULT_POLICIES
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("group_project_grants")
    op.drop_table("group_memberships")
    op.drop_table("groups")
    op.drop_table("policies")
