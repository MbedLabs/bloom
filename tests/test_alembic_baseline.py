import importlib.util
from pathlib import Path

import sqlalchemy as sa

from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.core.database import Base


def _load_revision_module(filename: str, module_name: str):
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initial_baseline_creates_base_schema(monkeypatch):
    revision = _load_revision_module(
        "ebbcbf973496_add_project_memberships.py",
        "bloom_alembic_ebbcbf973496_add_project_memberships",
    )
    bind = object()
    calls: list[object] = []
    monkeypatch.setattr(revision.op, "get_bind", lambda: bind)
    monkeypatch.setattr(
        Base.metadata,
        "create_all",
        lambda *, bind: calls.append(bind),
    )

    revision.upgrade()

    assert calls == [bind]


def test_a07_disables_previously_migrated_integrations_missing_credentials():
    revision = _load_revision_module(
        "d20260729a07_admin_email_change_workflow.py",
        "bloom_alembic_d20260729a07_admin_email_change_workflow",
    )
    engine = sa.create_engine("sqlite://")

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE users (" "id INTEGER PRIMARY KEY, " "pending_email VARCHAR(255)" ")"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE user_tokens ("
                "id INTEGER PRIMARY KEY, "
                "user_id INTEGER NOT NULL, "
                "purpose VARCHAR(64) NOT NULL, "
                "used_at DATETIME"
                ")"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE integration_settings ("
                "id INTEGER PRIMARY KEY, "
                "enabled BOOLEAN NOT NULL, "
                "token_encrypted TEXT, "
                "webhook_secret TEXT"
                ")"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO integration_settings "
                "(id, enabled, token_encrypted, webhook_secret) VALUES "
                "(1, TRUE, NULL, NULL), "
                "(2, TRUE, 'fernet:v1:token', 'fernet:v1:secret')"
            )
        )
        connection.execute(
            sa.text("INSERT INTO users (id, pending_email) " "VALUES (1, 'approved@example.com')")
        )
        connection.execute(
            sa.text(
                "INSERT INTO user_tokens (id, user_id, purpose, used_at) "
                "VALUES (1, 1, 'email_change', NULL)"
            )
        )

        revision.op = Operations(MigrationContext.configure(connection))
        revision.upgrade()

        rows = connection.execute(
            sa.text("SELECT id, enabled FROM integration_settings ORDER BY id")
        ).all()
        token_target = connection.execute(
            sa.text("SELECT target_email FROM user_tokens WHERE id = 1")
        ).scalar_one()

    assert rows == [(1, False), (2, True)]
    assert token_target == "approved@example.com"
