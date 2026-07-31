"""locked baseline schema

Revision ID: d20260731a09
Revises:
Create Date: 2026-07-31

Single locked baseline for the Bloom schema.

This replaces the previous chain, whose base revision built the schema by calling
``Base.metadata.create_all()``. Because that base always produced whatever the
models currently described, every later revision found its columns already
present on a fresh install and had to be written defensively with
inspect-then-add guards - and the real ALTER path was therefore never exercised
by the fresh-install CI check.

The revision identifier is deliberately kept as the previous head
(``d20260731a09``) so that databases already migrated to that head report the
same identifier, are seen as up to date, and are left untouched. No stamp or
manual step is required for an existing deployment.

The retired chain also carried data-only revisions (membership backfill,
relationship-type canonicalisation, credential encryption). Those are safe to
drop: on an empty database they match no rows, and every deployed database has
already applied them.

From here migrations are ordinary explicit DDL: a new revision alters this
baseline, so the empty-database CI check exercises the same statements a
deployed database will run.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d20260731a09"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Indexes that are not expressed on the SQLAlchemy models and were previously
# added by dedicated revisions. They must stay part of the baseline, otherwise a
# fresh install would silently lose them.
_PERFORMANCE_INDEXES = (
    ("ix_test_cases_tc_id", "test_cases", ["tc_id"]),
    ("ix_test_campaign_items_campaign_id", "test_campaign_items", ["campaign_id"]),
    ("ix_test_campaign_items_test_case_id", "test_campaign_items", ["test_case_id"]),
    ("ix_test_suite_items_suite_id", "test_suite_items", ["suite_id"]),
    ("ix_test_suite_items_test_case_id", "test_suite_items", ["test_case_id"]),
    ("ix_defects_project_id", "defects", ["project_id"]),
    (
        "ix_artefact_links_project_types",
        "artefact_links",
        ["project_id", "source_type", "target_type"],
    ),
)

# Trigram search indexes. Postgres-only, and skipped when pg_trgm cannot be
# installed - search then falls back to ILIKE.
_SEARCH_COLUMNS = (
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


def _trgm_index_name(table: str, column: str) -> str:
    return f"ix_trgm_{table}_{column}"


def _pg_trgm_available(bind) -> bool:
    row = bind.exec_driver_sql(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'pg_trgm'"
    ).fetchone()
    return row is not None


def _create_search_indexes() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    if not _pg_trgm_available(bind):
        # Extension not installable on this server; search still works via ILIKE.
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for table, column in _SEARCH_COLUMNS:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {_trgm_index_name(table, column)} "
            f'ON {table} USING gin ("{column}" gin_trgm_ops)'
        )


def _drop_search_indexes() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column in _SEARCH_COLUMNS:
        op.execute(f"DROP INDEX IF EXISTS {_trgm_index_name(table, column)}")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "artefact_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("artefact_type", sa.String(length=30), nullable=False),
        sa.Column("artefact_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_artefact_activities_artefact_id"),
        "artefact_activities",
        ["artefact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_artefact_activities_artefact_type"),
        "artefact_activities",
        ["artefact_type"],
        unique=False,
    )
    op.create_table(
        "artefact_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("artefact_type", sa.String(length=30), nullable=False),
        sa.Column("artefact_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_artefact_comments_artefact_id"), "artefact_comments", ["artefact_id"], unique=False
    )
    op.create_index(
        op.f("ix_artefact_comments_artefact_type"),
        "artefact_comments",
        ["artefact_type"],
        unique=False,
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=10), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("prefix"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role", sa.Enum("admin", "maintainer", "external", name="userrole"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("session_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("invited_at", sa.DateTime(), nullable=True),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=True),
        sa.Column("last_invite_sent_at", sa.DateTime(), nullable=True),
        sa.Column("invite_accepted_at", sa.DateTime(), nullable=True),
        sa.Column("password_set_at", sa.DateTime(), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
        sa.Column("pending_email", sa.String(length=255), nullable=True),
        sa.Column("email_change_status", sa.String(length=32), nullable=True),
        sa.Column("email_change_requested_at", sa.DateTime(), nullable=True),
        sa.Column("api_token_jti", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_table(
        "artefact_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("suspect", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type", "source_id", "target_type", "target_id", "role", name="uq_artefact_link"
        ),
    )
    op.create_index(
        op.f("ix_artefact_links_source_id"), "artefact_links", ["source_id"], unique=False
    )
    op.create_index(
        op.f("ix_artefact_links_source_type"), "artefact_links", ["source_type"], unique=False
    )
    op.create_index(
        op.f("ix_artefact_links_target_id"), "artefact_links", ["target_id"], unique=False
    )
    op.create_index(
        op.f("ix_artefact_links_target_type"), "artefact_links", ["target_type"], unique=False
    )
    op.create_table(
        "baselines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("baseline_id", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("baseline_type", sa.String(length=30), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "change_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("change_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("change_type", sa.String(length=30), nullable=False),
        sa.Column("impact_assessment", sa.Text(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("external_tracker", sa.String(length=20), nullable=True),
        sa.Column("external_repo_full_name", sa.String(length=255), nullable=True),
        sa.Column("external_issue_number", sa.Integer(), nullable=True),
        sa.Column("external_issue_url", sa.String(length=500), nullable=True),
        sa.Column("external_issue_state", sa.String(length=30), nullable=True),
        sa.Column("external_last_event_at", sa.DateTime(), nullable=True),
        sa.Column("source_ref", sa.String(length=100), nullable=True),
        sa.Column("source_project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_change_requests_external_issue",
        "change_requests",
        ["external_tracker", "external_repo_full_name", "external_issue_number"],
        unique=False,
    )
    op.create_table(
        "defects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("defect_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("reporter_id", sa.Integer(), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("external_tracker", sa.String(length=20), nullable=True),
        sa.Column("external_repo_full_name", sa.String(length=255), nullable=True),
        sa.Column("external_issue_number", sa.Integer(), nullable=True),
        sa.Column("external_issue_url", sa.String(length=500), nullable=True),
        sa.Column("external_issue_state", sa.String(length=30), nullable=True),
        sa.Column("external_last_event_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("doc_id", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("doc_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.String(length=100), nullable=True),
        sa.Column("source_project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "import_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_import_attempts_created_at"), "import_attempts", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_import_attempts_expires_at"), "import_attempts", ["expires_at"], unique=False
    )
    op.create_index(
        op.f("ix_import_attempts_project_id"), "import_attempts", ["project_id"], unique=False
    )
    op.create_index(
        op.f("ix_import_attempts_user_id"), "import_attempts", ["user_id"], unique=False
    )
    op.create_index(
        "uq_import_attempts_active_project",
        "import_attempts",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "integration_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("tracker", sa.String(length=20), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("account_email", sa.String(length=255), nullable=True),
        sa.Column("token_encrypted", sa.Text(), nullable=True),
        sa.Column("webhook_secret", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "tracker", name="uq_integration_project_tracker"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link_path", sa.String(length=500), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notifications_created_at"), "notifications", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_notifications_project_id"), "notifications", ["project_id"], unique=False
    )
    op.create_index(op.f("ix_notifications_read_at"), "notifications", ["read_at"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "project_id", name="uq_project_membership_user_project"),
    )
    op.create_table(
        "project_variables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "requirements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("req_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("req_type", sa.String(length=30), nullable=False),
        sa.Column("req_origin", sa.String(length=50), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("approver_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("source_ref", sa.String(length=100), nullable=True),
        sa.Column("source_project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["requirements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requirements_parent_id"), "requirements", ["parent_id"], unique=False)
    op.create_index(
        op.f("ix_requirements_project_id"), "requirements", ["project_id"], unique=False
    )
    op.create_table(
        "service_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("token_prefix", sa.String(length=24), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_service_credentials_expires_at"),
        "service_credentials",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_service_credentials_revoked_at"),
        "service_credentials",
        ["revoked_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_service_credentials_token_prefix"),
        "service_credentials",
        ["token_prefix"],
        unique=True,
    )
    op.create_table(
        "test_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("tc_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("approver_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("last_execution_status", sa.String(length=20), nullable=True),
        sa.Column("last_executed_at", sa.DateTime(), nullable=True),
        sa.Column("last_execution_comment", sa.Text(), nullable=True),
        sa.Column("last_bud_run_id", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.String(length=100), nullable=True),
        sa.Column("source_project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_test_cases_project_id"), "test_cases", ["project_id"], unique=False)
    op.create_table(
        "test_concepts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("linked_requirement_ids", sa.JSON(), nullable=True),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("source_ref", sa.String(length=100), nullable=True),
        sa.Column("source_project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_suites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("suite_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "purpose",
            sa.Enum(
                "invite",
                "email_verification",
                "password_reset",
                "refresh",
                "email_change",
                name="usertokenpurpose",
            ),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("target_email", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_tokens_expires_at"), "user_tokens", ["expires_at"], unique=False)
    op.create_index(op.f("ix_user_tokens_token_hash"), "user_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_user_tokens_used_at"), "user_tokens", ["used_at"], unique=False)
    op.create_index(op.f("ix_user_tokens_user_id"), "user_tokens", ["user_id"], unique=False)
    op.create_table(
        "change_request_sync_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("change_request_id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("tracker", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload_summary", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("external_event_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["change_request_id"],
            ["change_requests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_change_request_sync_events_change_request_id"),
        "change_request_sync_events",
        ["change_request_id"],
        unique=False,
    )
    op.create_table(
        "defect_sync_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defect_id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("tracker", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload_summary", sa.Text(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("external_event_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["defect_id"],
            ["defects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "design_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("design_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("design_type", sa.String(length=30), nullable=False),
        sa.Column("linked_requirement_id", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.String(length=100), nullable=True),
        sa.Column("source_project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["linked_requirement_id"],
            ["requirements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "document_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("parent_section_id", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("section_type", sa.String(length=30), nullable=False),
        sa.Column("linked_requirement_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["linked_requirement_id"],
            ["requirements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["parent_section_id"],
            ["document_sections.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project_external_doc_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["project_memberships.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("membership_id", "doc_type", name="uq_external_doc_type_membership"),
    )
    op.create_table(
        "requirement_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["requirements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["requirements.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "target_id", "link_type", name="uq_req_link"),
    )
    op.create_table(
        "risk_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("risk_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("probability", sa.String(length=20), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("risk_category", sa.String(length=30), nullable=False),
        sa.Column("linked_requirement_id", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.String(length=100), nullable=True),
        sa.Column("source_project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["linked_requirement_id"],
            ["requirements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.String(length=50), nullable=True),
        sa.Column("suite_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("bud_run_id", sa.Integer(), nullable=True),
        sa.Column("bud_run_url", sa.String(length=500), nullable=True),
        sa.Column("bud_run_status", sa.String(length=50), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["suite_id"],
            ["test_suites.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_run_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("test_run_id", sa.Integer(), nullable=False),
        sa.Column("test_run_name", sa.String(length=255), nullable=True),
        sa.Column("teststation_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["requirements.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "test_suite_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("suite_id", sa.Integer(), nullable=False),
        sa.Column("test_case_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["suite_id"],
            ["test_suites.id"],
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("suite_id", "test_case_id", name="uq_suite_tc"),
    )
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("integration_setting_id", sa.Integer(), nullable=False),
        sa.Column("tracker", sa.String(length=20), nullable=False),
        sa.Column("delivery_id", sa.String(length=255), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["integration_setting_id"], ["integration_settings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracker", "delivery_id", name="uq_webhook_tracker_delivery"),
    )
    op.create_index(
        op.f("ix_webhook_deliveries_integration_setting_id"),
        "webhook_deliveries",
        ["integration_setting_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_deliveries_received_at"),
        "webhook_deliveries",
        ["received_at"],
        unique=False,
    )
    op.create_table(
        "campaign_suites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("suite_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["test_campaigns.id"],
        ),
        sa.ForeignKeyConstraint(
            ["suite_id"],
            ["test_suites.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "suite_id", name="uq_campaign_suite"),
    )
    op.create_table(
        "test_campaign_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("test_case_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["test_campaigns.id"],
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    for name, table, columns in _PERFORMANCE_INDEXES:
        op.create_index(name, table, columns, unique=False)

    _create_search_indexes()


def downgrade() -> None:
    _drop_search_indexes()

    for name, table, _columns in reversed(_PERFORMANCE_INDEXES):
        op.drop_index(name, table_name=table)

    """Downgrade schema."""
    op.drop_table("test_campaign_items")
    op.drop_table("campaign_suites")
    op.drop_index(op.f("ix_webhook_deliveries_received_at"), table_name="webhook_deliveries")
    op.drop_index(
        op.f("ix_webhook_deliveries_integration_setting_id"), table_name="webhook_deliveries"
    )
    op.drop_table("webhook_deliveries")
    op.drop_table("test_suite_items")
    op.drop_table("test_run_links")
    op.drop_table("test_campaigns")
    op.drop_table("risk_items")
    op.drop_table("requirement_links")
    op.drop_table("project_external_doc_types")
    op.drop_table("document_sections")
    op.drop_table("design_items")
    op.drop_table("defect_sync_events")
    op.drop_index(
        op.f("ix_change_request_sync_events_change_request_id"),
        table_name="change_request_sync_events",
    )
    op.drop_table("change_request_sync_events")
    op.drop_index(op.f("ix_user_tokens_user_id"), table_name="user_tokens")
    op.drop_index(op.f("ix_user_tokens_used_at"), table_name="user_tokens")
    op.drop_index(op.f("ix_user_tokens_token_hash"), table_name="user_tokens")
    op.drop_index(op.f("ix_user_tokens_expires_at"), table_name="user_tokens")
    op.drop_table("user_tokens")
    op.drop_table("test_suites")
    op.drop_table("test_concepts")
    op.drop_index(op.f("ix_test_cases_project_id"), table_name="test_cases")
    op.drop_table("test_cases")
    op.drop_index(op.f("ix_service_credentials_token_prefix"), table_name="service_credentials")
    op.drop_index(op.f("ix_service_credentials_revoked_at"), table_name="service_credentials")
    op.drop_index(op.f("ix_service_credentials_expires_at"), table_name="service_credentials")
    op.drop_table("service_credentials")
    op.drop_index(op.f("ix_requirements_project_id"), table_name="requirements")
    op.drop_index(op.f("ix_requirements_parent_id"), table_name="requirements")
    op.drop_table("requirements")
    op.drop_table("project_variables")
    op.drop_table("project_memberships")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_read_at"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_project_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_created_at"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("integration_settings")
    op.drop_index(
        "uq_import_attempts_active_project",
        table_name="import_attempts",
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    op.drop_index(op.f("ix_import_attempts_user_id"), table_name="import_attempts")
    op.drop_index(op.f("ix_import_attempts_project_id"), table_name="import_attempts")
    op.drop_index(op.f("ix_import_attempts_expires_at"), table_name="import_attempts")
    op.drop_index(op.f("ix_import_attempts_created_at"), table_name="import_attempts")
    op.drop_table("import_attempts")
    op.drop_table("documents")
    op.drop_table("defects")
    op.drop_index("ix_change_requests_external_issue", table_name="change_requests")
    op.drop_table("change_requests")
    op.drop_table("baselines")
    op.drop_index(op.f("ix_artefact_links_target_type"), table_name="artefact_links")
    op.drop_index(op.f("ix_artefact_links_target_id"), table_name="artefact_links")
    op.drop_index(op.f("ix_artefact_links_source_type"), table_name="artefact_links")
    op.drop_index(op.f("ix_artefact_links_source_id"), table_name="artefact_links")
    op.drop_table("artefact_links")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("projects")
    op.drop_index(op.f("ix_artefact_comments_artefact_type"), table_name="artefact_comments")
    op.drop_index(op.f("ix_artefact_comments_artefact_id"), table_name="artefact_comments")
    op.drop_table("artefact_comments")
    op.drop_index(op.f("ix_artefact_activities_artefact_type"), table_name="artefact_activities")
    op.drop_index(op.f("ix_artefact_activities_artefact_id"), table_name="artefact_activities")
    op.drop_table("artefact_activities")

    # Alembic's autogenerate drops tables but not the enum types they use, which
    # would make a re-upgrade fail with "type already exists".
    for enum_name in ("userrole", "usertokenpurpose"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
