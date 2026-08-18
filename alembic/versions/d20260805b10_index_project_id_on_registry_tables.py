"""index project_id on the registry tables

Revision ID: d20260805b10
Revises: d20260731a09
Create Date: 2026-08-05

Every screen in Bloom is scoped to a project, so `WHERE project_id = ?` is the
most-run predicate in the application - and six of the ten tables the document
registry reads had no index that could serve it. `EXPLAIN` on a seeded database
confirms a sequential scan per table per request:

    Seq Scan on design_items
      Filter: (project_id = 1)

Requirements, test cases and defects already had one; these six did not.
Campaigns had only a partial unique index on `(project_id, campaign_id) WHERE
campaign_id IS NOT NULL`, which cannot serve a plain project lookup for a
campaign that has no identifier yet, so it gets a plain one too.

Documents additionally take `(project_id, doc_type)`: that table backs four
document kinds at once and is always read with both columns, once per kind.

Created concurrently is deliberately *not* used - these run inside the
migration's transaction, which is what makes the upgrade atomic, and the tables
are small enough for the brief write lock to be unremarkable. A deployment with
a very large document set should build them with CONCURRENTLY by hand first;
`IF NOT EXISTS` makes this revision a no-op afterwards.
"""

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
