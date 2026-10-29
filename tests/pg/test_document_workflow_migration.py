"""The consolidated workflow migration matches models and preserves existing rows."""

import re

from sqlalchemy import inspect, text

from app.models import ArtefactComment
from app.models.workflow import (
    ArtefactRequest,
    ArtefactRequestRecipient,
    ArtefactRevision,
    ArtefactRevisionFile,
    ArtefactWorkflow,
)
from tests.pg.test_link_rules_enforcement import _upgrade, database


def _schema_state(connection, table):
    """Read columns, keys and constraints in the transaction-isolated schema."""
    inspector = inspect(connection)
    schema = connection.info["link_test_schema"]
    return {
        "columns": inspector.get_columns(table.name, schema=schema),
        "primary": inspector.get_pk_constraint(table.name, schema=schema),
        "unique": inspector.get_unique_constraints(table.name, schema=schema),
        "foreign": inspector.get_foreign_keys(table.name, schema=schema),
        "checks": inspector.get_check_constraints(table.name, schema=schema),
        "indexes": inspector.get_indexes(table.name, schema=schema),
    }


async def test_workflow_migration_schema_matches_the_orm_models(database):
    connection, session, project = database
    await connection.run_sync(_upgrade, "head")
    for model in (
        ArtefactWorkflow,
        ArtefactRevision,
        ArtefactRequest,
        ArtefactRequestRecipient,
        ArtefactRevisionFile,
    ):
        table = model.__table__
        state = await connection.run_sync(_schema_state, table)
        assert {column["name"] for column in state["columns"]} == set(table.columns.keys())
        for column in state["columns"]:
            expected = table.c[column["name"]]
            assert column["nullable"] == expected.nullable
            assert (
                str(column["type"].compile(dialect=connection.dialect)).upper()
                == str(expected.type.compile(dialect=connection.dialect)).upper()
            )
        assert state["primary"]["constrained_columns"] == [
            column.name for column in table.primary_key
        ]
        expected_unique = {
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        }
        assert {
            tuple(constraint["column_names"]) for constraint in state["unique"]
        } == expected_unique
        expected_foreign = {
            (
                tuple(column.name for column in constraint.columns),
                tuple(element.target_fullname for element in constraint.elements),
                constraint.ondelete,
            )
            for constraint in table.foreign_key_constraints
        }
        actual_foreign = {
            (
                tuple(constraint["constrained_columns"]),
                tuple(
                    f"{constraint['referred_table']}.{column}"
                    for column in constraint["referred_columns"]
                ),
                constraint["options"].get("ondelete"),
            )
            for constraint in state["foreign"]
        }
        assert actual_foreign == expected_foreign
        assert {constraint["name"] for constraint in state["checks"]} == {
            constraint.name
            for constraint in table.constraints
            if constraint.__class__.__name__ == "CheckConstraint"
        }
        for constraint in state["checks"]:
            expected = next(item for item in table.constraints if item.name == constraint["name"])
            assert re.findall(r"'([^']*)'", constraint["sqltext"]) == re.findall(
                r"'([^']*)'", str(expected.sqltext)
            )
            field = str(expected.sqltext).split()[0]
            assert re.search(rf"\b{field}\b", constraint["sqltext"])
        if model is ArtefactRequest:
            pending = next(
                index
                for index in state["indexes"]
                if index["name"] == "uq_artefact_requests_pending_cycle"
            )
            assert pending["unique"] is True
            assert pending["column_names"] == ["workflow_id", "revision_number", "kind"]
            predicate = re.sub(
                r"::[a-z ]+", "", str(pending["dialect_options"]["postgresql_where"])
            )
            assert re.sub(r"[()\s]", "", predicate) == "status='pending'"
    state = await connection.run_sync(_schema_state, ArtefactComment.__table__)
    actual = {column["name"]: column for column in state["columns"]}
    for name in ("revision_number", "content_hash", "review_request_id"):
        expected = ArtefactComment.__table__.c[name]
        assert actual[name]["nullable"] is True
        assert (
            str(actual[name]["type"].compile(dialect=connection.dialect)).upper()
            == str(expected.type.compile(dialect=connection.dialect)).upper()
        )
    assert any(
        constraint["constrained_columns"] == ["review_request_id"]
        and constraint["referred_table"] == "artefact_requests"
        and constraint["options"].get("ondelete") == "SET NULL"
        for constraint in state["foreign"]
    )


async def test_workflow_migration_does_not_rewrite_legacy_status_actors_or_baselines(database):
    connection, session, project = database
    await connection.execute(text("UPDATE requirements SET status = 'Approved' WHERE id = 1"))
    await connection.execute(
        text(
            "INSERT INTO change_requests (project_id, change_id, title, status, visibility, priority, "
            "change_type, created_at, updated_at) VALUES (:project, 'PRJ-CHG-001', 'Legacy', "
            "'Implemented', 'internal', 'Medium', 'Enhancement', now(), now())"
        ),
        {"project": project},
    )
    await connection.execute(
        text(
            "INSERT INTO baselines (project_id, name, status, baseline_type, snapshot, created_at, updated_at) "
            "VALUES (:project, 'Frozen', 'Open', 'Milestone', '{\"legacy\": true}', now(), now())"
        ),
        {"project": project},
    )
    before = (
        await connection.execute(text("SELECT id, status FROM requirements ORDER BY id"))
    ).all()
    baseline = await connection.scalar(text("SELECT snapshot::text FROM baselines"))
    await connection.run_sync(_upgrade, "head")
    assert (
        await connection.execute(text("SELECT id, status FROM requirements ORDER BY id"))
    ).all() == before
    assert await connection.scalar(text("SELECT status FROM change_requests")) == "Implemented"
    assert await connection.scalar(text("SELECT snapshot::text FROM baselines")) == baseline
    assert await connection.scalar(text("SELECT count(*) FROM artefact_workflows")) == 0
    assert await connection.scalar(text("SELECT count(*) FROM artefact_revisions")) == 0
    assert await connection.scalar(text("SELECT count(*) FROM artefact_requests")) == 0
