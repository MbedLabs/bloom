"""add import attempts

Revision ID: d20260722a01
Revises: e1f2a3b4c5d6
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d20260722a01"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "import_attempts" in inspector.get_table_names():
        return
    op.create_table(
        "import_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_attempts_user_id", "import_attempts", ["user_id"])
    op.create_index("ix_import_attempts_project_id", "import_attempts", ["project_id"])
    op.create_index("ix_import_attempts_created_at", "import_attempts", ["created_at"])
    op.create_index("ix_import_attempts_expires_at", "import_attempts", ["expires_at"])
    op.create_index(
        "uq_import_attempts_active_project",
        "import_attempts",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_table("import_attempts")
