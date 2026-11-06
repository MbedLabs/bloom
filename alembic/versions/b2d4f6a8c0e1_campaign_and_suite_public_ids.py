"""test_campaigns and test_suites: a unique public ID on every row

Revision ID: b2d4f6a8c0e1
Revises: 0ef8b87db4d3
Create Date: 2026-10-31

Gives every campaign without a public ID the next free one of its project, in database id
order, in the format of the application's id generator (PRJ-CMP-001, widened past 999).
Refuses to run while two suites or two campaigns share a public ID. Then makes the campaign
public ID required and both public IDs unique.
"""

import re

import sqlalchemy as sa
from alembic import op

revision = "b2d4f6a8c0e1"
down_revision = "0ef8b87db4d3"
branch_labels = None
depends_on = None

MIN_WIDTH = 3


def _assign_missing_campaign_ids(bind) -> None:
    """Give each campaign without a public ID the next one of its project."""
    projects = bind.execute(
        sa.text(
            "SELECT DISTINCT p.id, p.prefix FROM projects p "
            "JOIN test_campaigns c ON c.project_id = p.id "
            "WHERE c.campaign_id IS NULL OR c.campaign_id = '' ORDER BY p.id"
        )
    ).all()
    for project_id, prefix in projects:
        stem = f"{prefix}-CMP-"
        pattern = re.compile(rf"^{re.escape(stem)}(\d+)$")
        rows = bind.execute(
            sa.text(
                "SELECT id, campaign_id FROM test_campaigns WHERE project_id = :project ORDER BY id"
            ),
            {"project": project_id},
        ).all()
        suffixes = {
            row_id: match.group(1)
            for row_id, value in rows
            if value and (match := pattern.match(value))
        }
        missing = [row_id for row_id, value in rows if not value]
        start = max((int(suffix) for suffix in suffixes.values()), default=0) + 1
        width = max(MIN_WIDTH, len(str(start + len(missing) - 1)))
        renames = {
            row_id: int(suffix) for row_id, suffix in suffixes.items() if len(suffix) < width
        }
        values = {**renames, **{row_id: start + n for n, row_id in enumerate(missing)}}
        for row_id, number in values.items():
            bind.execute(
                sa.text("UPDATE test_campaigns SET campaign_id = :value WHERE id = :id"),
                {"value": f"{stem}{number:0{width}d}", "id": row_id},
            )


DUPLICATE_QUERIES = {
    "test_suites.suite_id": "SELECT suite_id FROM test_suites "
    "GROUP BY suite_id HAVING COUNT(*) > 1 ORDER BY suite_id",
    "test_campaigns.campaign_id": "SELECT campaign_id FROM test_campaigns "
    "GROUP BY campaign_id HAVING COUNT(*) > 1 ORDER BY campaign_id",
}


def _refuse_duplicates(bind) -> None:
    """Stop the upgrade when two suites or two campaigns share a public ID."""
    for column, query in DUPLICATE_QUERIES.items():
        duplicates = bind.execute(sa.text(query)).scalars().all()
        if duplicates:
            raise RuntimeError(
                f"{column} holds duplicate public IDs: {', '.join(duplicates)}. "
                "Give each row its own public ID, then upgrade again."
            )


def upgrade() -> None:
    """Fill the missing campaign public IDs, then require both public IDs and make them unique."""
    bind = op.get_bind()
    _assign_missing_campaign_ids(bind)
    _refuse_duplicates(bind)
    op.alter_column(
        "test_campaigns", "campaign_id", existing_type=sa.String(length=50), nullable=False
    )
    op.create_index("uq_test_suites_suite_id", "test_suites", ["suite_id"], unique=True)
    op.create_index("uq_test_campaigns_campaign_id", "test_campaigns", ["campaign_id"], unique=True)


def downgrade() -> None:
    """Drop the unique indexes and make the campaign public ID optional; assigned IDs stay."""
    op.drop_index("uq_test_campaigns_campaign_id", table_name="test_campaigns")
    op.drop_index("uq_test_suites_suite_id", table_name="test_suites")
    op.alter_column(
        "test_campaigns", "campaign_id", existing_type=sa.String(length=50), nullable=True
    )
