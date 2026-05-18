"""add_project_memberships

Revision ID: ebbcbf973496
Revises:
Create Date: 2026-05-18 09:51:26.002452

Project-scoped role assignments:
- project_memberships: per-user per-project role (maintainer/external).
  Admins skip this table — their global User.role suffices.
- project_external_doc_types: doc-type visibility whitelist for external
  users. Empty rows set → external user sees nothing (deny-by-default).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ebbcbf973496"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column(
            "role", sa.String(20), nullable=False, server_default="external"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "user_id", "project_id", name="uq_project_membership_user_project"
        ),
    )

    op.create_table(
        "project_external_doc_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "membership_id",
            sa.Integer(),
            sa.ForeignKey("project_memberships.id"),
            nullable=False,
        ),
        sa.Column("doc_type", sa.String(30), nullable=False),
        sa.UniqueConstraint(
            "membership_id", "doc_type", name="uq_external_doc_type_membership"
        ),
    )


def downgrade() -> None:
    op.drop_table("project_external_doc_types")
    op.drop_table("project_memberships")
