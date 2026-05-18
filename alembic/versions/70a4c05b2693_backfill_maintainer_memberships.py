"""backfill_maintainer_memberships

Revision ID: 70a4c05b2693
Revises: ebbcbf973496
Create Date: 2026-05-18 09:51:52.000000

For every existing active maintainer (User.role='maintainer'), create a
project_memberships row for every existing project with role='maintainer'.
Ensures no existing maintainer loses access when the project-scoped check
goes live.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "70a4c05b2693"
down_revision: Union[str, Sequence[str], None] = "ebbcbf973496"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            INSERT INTO project_memberships (user_id, project_id, role, created_at, updated_at)
            SELECT u.id, p.id, 'maintainer', NOW(), NOW()
            FROM users u
            CROSS JOIN projects p
            WHERE u.role = 'maintainer'
              AND u.is_active = TRUE
            ON CONFLICT (user_id, project_id) DO NOTHING
        """)
    )


def downgrade() -> None:
    # Additive migration — reverse is no-op
    pass
