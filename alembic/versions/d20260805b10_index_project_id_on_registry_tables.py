"""index project_id on the registry tables"""

from alembic import op

revision = "d20260805b10"
down_revision = "d20260731a09"
branch_labels = None
depends_on = None


# (index name, table, columns) - the tables the registry union reads that had
# no index leading on project_id.
_INDEXES = [
    ("ix_design_items_project_id", "design_items", "project_id"),
    ("ix_risk_items_project_id", "risk_items", "project_id"),
    ("ix_change_requests_project_id", "change_requests", "project_id"),
    ("ix_test_concepts_project_id", "test_concepts", "project_id"),
    ("ix_test_suites_project_id", "test_suites", "project_id"),
    ("ix_test_campaigns_project_id", "test_campaigns", "project_id"),
    ("ix_baselines_project_id", "baselines", "project_id"),
    ("ix_documents_project_id_doc_type", "documents", "project_id, doc_type"),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})")


def downgrade() -> None:
    for name, _table, _columns in reversed(_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")
