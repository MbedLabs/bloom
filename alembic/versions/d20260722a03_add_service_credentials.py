"""add scoped service credentials

Revision ID: d20260722a03
Revises: d20260722a02
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d20260722a03"
down_revision: Union[str, Sequence[str], None] = "d20260722a02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "service_credentials" not in inspector.get_table_names():
        op.create_table(
            "service_credentials",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("token_prefix", sa.String(length=24), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("scope", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index(
            "ix_service_credentials_token_prefix",
            "service_credentials",
            ["token_prefix"],
            unique=True,
        )
        op.create_index(
            "ix_service_credentials_expires_at",
            "service_credentials",
            ["expires_at"],
        )
        op.create_index(
            "ix_service_credentials_revoked_at",
            "service_credentials",
            ["revoked_at"],
        )
    # Revoke every legacy one-year full-admin integration JWT during migration.
    op.execute(sa.text("UPDATE users SET api_token_jti = NULL"))


def downgrade() -> None:
    op.drop_table("service_credentials")
