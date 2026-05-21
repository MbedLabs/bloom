"""performance_indexes

Revision ID: a1b2c3d4e5f6
Revises: 70a4c05b2693
Create Date: 2026-05-20

Adds indexes for high-frequency FK lookups (Sprint 1 / DEF-009).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "70a4c05b2693"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_test_cases_tc_id",
        "test_cases",
        ["tc_id"],
        unique=False,
    )
    op.create_index(
        "ix_test_campaign_items_campaign_id",
        "test_campaign_items",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_test_campaign_items_test_case_id",
        "test_campaign_items",
        ["test_case_id"],
        unique=False,
    )
    op.create_index(
        "ix_test_suite_items_suite_id",
        "test_suite_items",
        ["suite_id"],
        unique=False,
    )
    op.create_index(
        "ix_test_suite_items_test_case_id",
        "test_suite_items",
        ["test_case_id"],
        unique=False,
    )
    op.create_index(
        "ix_defects_project_id",
        "defects",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_artefact_links_project_types",
        "artefact_links",
        ["project_id", "source_type", "target_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_artefact_links_project_types", table_name="artefact_links")
    op.drop_index("ix_defects_project_id", table_name="defects")
    op.drop_index("ix_test_suite_items_test_case_id", table_name="test_suite_items")
    op.drop_index("ix_test_suite_items_suite_id", table_name="test_suite_items")
    op.drop_index("ix_test_campaign_items_test_case_id", table_name="test_campaign_items")
    op.drop_index("ix_test_campaign_items_campaign_id", table_name="test_campaign_items")
    op.drop_index("ix_test_cases_tc_id", table_name="test_cases")
