"""Allow distinct project policy bundles for the same person."""

import sqlalchemy as sa

from alembic import op

revision = "9e4a2c7d18b0"
down_revision = "8134a1512496"
branch_labels = None
depends_on = None


def upgrade():
    """Replace direct-entry uniqueness without modifying existing grants."""
    op.create_unique_constraint(
        "uq_project_access_project_user_bundle",
        "project_access",
        ["project_id", "user_id", "policy_group_id"],
    )
    op.create_index(
        "uq_project_access_project_legacy_user",
        "project_access",
        ["project_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL AND policy_group_id IS NULL"),
    )
    op.drop_constraint("uq_project_access_project_user", "project_access", type_="unique")


def downgrade():
    """Restore single-entry uniqueness only when every grant can be retained."""
    overlap = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM project_access WHERE user_id IS NOT NULL "
                "GROUP BY project_id, user_id HAVING count(*) > 1 LIMIT 1"
            )
        )
        .first()
    )
    if overlap is not None:
        raise RuntimeError(
            "Cannot downgrade while overlapping project groups exist; "
            "existing grants cannot be represented by a single project entry"
        )
    op.create_unique_constraint(
        "uq_project_access_project_user", "project_access", ["project_id", "user_id"]
    )
    op.drop_index("uq_project_access_project_legacy_user", table_name="project_access")
    op.drop_constraint("uq_project_access_project_user_bundle", "project_access", type_="unique")
