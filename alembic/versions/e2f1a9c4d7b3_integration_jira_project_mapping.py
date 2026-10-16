"""integration_settings: jira project key and inbound defect creation

Revision ID: e2f1a9c4d7b3
Revises: d20260907f14
Create Date: 2026-09-19

"""

import sqlalchemy as sa

from alembic import op

revision = "e2f1a9c4d7b3"
down_revision = "d20260907f14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the Jira project-key mapping and the inbound-creation flag."""
    op.add_column(
        "integration_settings",
        sa.Column("jira_project_key", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "integration_settings",
        sa.Column(
            "create_defects_on_inbound",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_unique_constraint(
        "uq_integration_jira_project_key",
        "integration_settings",
        ["tracker", "jira_project_key"],
    )


def downgrade() -> None:
    """Drop the Jira project-key mapping and the inbound-creation flag."""
    op.drop_constraint("uq_integration_jira_project_key", "integration_settings", type_="unique")
    op.drop_column("integration_settings", "create_defects_on_inbound")
    op.drop_column("integration_settings", "jira_project_key")
