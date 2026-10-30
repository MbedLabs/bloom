"""PostgreSQL link rules preserve old rows and reject new forbidden triples."""

import json
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "e1a7c3f9b204"
CONSTRAINT = "fk_artefact_links_allowed_triple"


def _upgrade(connection, revision):
    """Run the real Alembic revision chain on the supplied isolated connection."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    context = MigrationContext.configure(
        connection,
        opts={
            "fn": lambda current, ctx: scripts._upgrade_revs(revision, current),
            "version_table_schema": connection.info["link_test_schema"],
        },
    )
    with Operations.context(context):
        context.run_migrations()


@pytest_asyncio.fixture
async def database():
    """Migrate an isolated schema inside a rolled-back transaction."""
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        schema = "link_rules_" + uuid.uuid4().hex
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.info["link_test_schema"] = schema
        await connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
        try:
            await connection.run_sync(_upgrade, BEFORE)
            project = await connection.scalar(
                text(
                    "INSERT INTO projects (name, prefix, status, created_at, updated_at) "
                    "VALUES ('Link rules', 'PRJ', 'Active', now(), now()) RETURNING id"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO requirements (project_id, req_id, title, status, priority, req_type, req_origin, visibility, created_at, "
                    "updated_at) VALUES (:project, 'PRJ-REQ-001', 'First', 'Draft', 'Medium', 'Functional', 'Internal', 'internal', now(), now()), "
                    "(:project, 'PRJ-REQ-002', 'Second', 'Draft', 'Medium', 'Functional', 'Internal', 'internal', now(), now())"
                ),
                {"project": project},
            )
            async with AsyncSession(bind=connection, expire_on_commit=False) as session:
                yield connection, session, project
        finally:
            await transaction.rollback()
    await engine.dispose()


async def _insert(connection, project, source="REQ", target="REQ", role="forbidden"):
    """Insert a direct SQL link with the supplied storage triple."""
    return await connection.scalar(
        text(
            "INSERT INTO artefact_links (project_id, source_type, source_id, target_type, "
            "target_id, role, suspect, created_at) "
            "VALUES (:project, :source, 1, :target, 2, :role, false, now()) RETURNING id"
        ),
        {"project": project, "source": source, "target": target, "role": role},
    )


async def _validated(connection):
    """Read whether the link constraint has been validated."""
    return await connection.scalar(
        text(
            "SELECT convalidated FROM pg_constraint WHERE conname = :constraint "
            "AND conrelid = 'artefact_links'::regclass"
        ),
        {"constraint": CONSTRAINT},
    )


async def test_migration_preserves_invalid_rows_and_operator_refuses_validation(database):
    from app.tools.check_link_rules import check_link_rules

    connection, session, project = database
    old_id = await _insert(connection, project)
    await connection.execute(
        text(
            "INSERT INTO requirement_links (source_id, target_id, link_type, created_at) "
            "VALUES (1, 2, 'derived_from', now())"
        )
    )
    await connection.run_sync(_upgrade, "head")
    assert await _validated(connection) is False
    assert await connection.scalar(text("SELECT id FROM artefact_links")) == old_id
    lines = []
    assert await check_link_rules(session, validate=True, emit=lines.append) == 1
    report = [json.loads(line) for line in lines]
    invalid = next(row for row in report if row["table"] == "artefact_links")
    legacy = next(row for row in report if row["table"] == "requirement_links")
    assert invalid["id"] == old_id
    assert invalid["role"] == "forbidden"
    assert legacy["link_type"] == "derived_from"
    assert legacy["mapped_role"] == "derives_from"
    assert await _validated(connection) is False
    await connection.execute(
        text("UPDATE artefact_links SET role = 'refines' WHERE id = :id"), {"id": old_id}
    )
    assert await check_link_rules(session, validate=True, emit=lines.append) == 0
    assert await _validated(connection) is True
    assert await connection.scalar(text("SELECT count(*) FROM requirement_links")) == 1
    assert await connection.scalar(text("SELECT count(*) FROM artefact_links")) == 1


@pytest.mark.parametrize(
    ("source", "target", "role"),
    [("REQ", "REQ", "forbidden"), ("TC", "REQ", "references"), ("UNKNOWN", "REQ", "refines")],
)
async def test_database_rejects_new_invalid_storage_triples(database, source, target, role):
    connection, session, project = database
    await connection.run_sync(_upgrade, "head")
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError) as rejected:
        async with savepoint:
            await _insert(connection, project, source, target, role)
    assert CONSTRAINT in str(rejected.value)


@pytest.mark.parametrize(
    ("source", "target", "role"),
    [
        ("TCO", "PROT", "references"),
        ("PROT", "TCO", "implements"),
        ("REQ", "REQ", "references"),
        ("REQ", "REQ", "refines"),
    ],
)
async def test_database_accepts_tag_and_alias_storage_triples(database, source, target, role):
    connection, session, project = database
    await connection.run_sync(_upgrade, "head")
    assert await _insert(connection, project, source, target, role)


async def test_migrated_allowed_table_equals_current_code_rules(database):
    from app.core.link_rules import allowed_link_triples

    connection, session, project = database
    await connection.run_sync(_upgrade, "head")
    rows = (
        await connection.execute(
            text("SELECT source_type, target_type, role FROM allowed_link_triples")
        )
    ).all()
    assert {tuple(row) for row in rows} == set(allowed_link_triples())
