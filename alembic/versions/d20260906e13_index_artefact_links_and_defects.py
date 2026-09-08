"""index the project scope on artefact links and defects"""

from alembic import op

revision = "d20260906e13"
down_revision = "d20260812d12"
branch_labels = None
depends_on = None


_INDEXES = [
    (
        "ix_artefact_links_project_scope",
        "artefact_links",
        "project_id, source_type, target_type, role",
    ),
    ("ix_defects_project_id", "defects", "project_id"),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})")


def downgrade() -> None:
    for name, _table, _columns in reversed(_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name}")
