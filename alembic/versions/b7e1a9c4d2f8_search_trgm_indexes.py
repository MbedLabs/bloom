"""Add pg_trgm GIN indexes for global search columns (Postgres only).

Revision ID: b7e1a9c4d2f8
Revises: f1c2d3e4b5a6
Create Date: 2026-07-17
"""

from alembic import op

revision = "b7e1a9c4d2f8"
down_revision = "f1c2d3e4b5a6"
branch_labels = None
depends_on = None

# (table, column) pairs matching app/core/search_registry.py
SEARCH_COLUMNS = (
    ("requirements", "req_id"),
    ("requirements", "title"),
    ("test_cases", "tc_id"),
    ("test_cases", "title"),
    ("documents", "doc_id"),
    ("documents", "title"),
    ("design_items", "design_id"),
    ("design_items", "title"),
    ("risk_items", "risk_id"),
    ("risk_items", "title"),
    ("change_requests", "change_id"),
    ("change_requests", "title"),
    ("test_concepts", "concept_id"),
    ("test_concepts", "name"),
    ("defects", "defect_id"),
    ("defects", "title"),
    ("test_suites", "suite_id"),
    ("test_suites", "name"),
    ("test_campaigns", "campaign_id"),
    ("test_campaigns", "name"),
)


def _index_name(table: str, column: str) -> str:
    return f"ix_trgm_{table}_{column}"


def _pg_trgm_available(bind) -> bool:
    row = bind.exec_driver_sql(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'pg_trgm'"
    ).fetchone()
    return row is not None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    if not _pg_trgm_available(bind):
        # Extension not installable on this server; search still works via ILIKE.
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for table, column in SEARCH_COLUMNS:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {_index_name(table, column)} "
            f'ON {table} USING gin ("{column}" gin_trgm_ops)'
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column in SEARCH_COLUMNS:
        op.execute(f"DROP INDEX IF EXISTS {_index_name(table, column)}")
