"""index the project scope on artefact links and defects

Revision ID: d20260906e13
Revises: d20260812d12
Create Date: 2026-09-06

Two tables were still missing an index that can serve `WHERE project_id = ?`.
Both sit on the project list, which computes coverage and a defect count for
every project shown.

`artefact_links` is the traceability table and the more important of the two. It
carried four single-column indexes - source_type, source_id, target_type,
target_id - and a unique constraint on
`(source_type, source_id, target_type, target_id, role)`, but nothing leading on
project_id, and `role` only as that constraint's fifth column, which cannot
serve a lookup. The coverage query filters all four of project_id, source_type,
target_type and role together, so it gets one composite in that order. The
leading column also serves the plain `project_id` filters this table takes in
fifteen other places.

`defects` had only its primary key. An earlier revision's note claimed defects
were already covered; `pg_indexes` says otherwise, so it gets a plain index.

Four other tables looked unindexed in the models but are not: project_variables
and integration_settings are served by unique constraints whose leading column
is project_id, and import_attempts and notifications already have explicit
indexes. They are deliberately left alone.

Not created concurrently, for the reason given in d20260805b10: these run inside
the migration transaction, which is what makes the upgrade atomic. A deployment
with a very large link table can build them with CONCURRENTLY by hand first;
`IF NOT EXISTS` makes this revision a no-op afterwards.
"""

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
