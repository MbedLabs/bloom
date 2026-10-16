"""A database created before the locked baseline gets the column and table it lacks."""

import asyncio
import importlib.util
import os
from pathlib import Path

import asyncpg
import pytest

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "e1a7c3f9b204_repair_pre_baseline_schema.py"
)


def _repair_statements():
    spec = importlib.util.spec_from_file_location("repair_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.REPAIR_STATEMENTS


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("needs PostgreSQL")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _repair_on_a_pre_baseline_schema():
    conn = await asyncpg.connect(_dsn())
    transaction = conn.transaction()
    await transaction.start()
    try:
        await conn.execute("ALTER TABLE integration_settings DROP COLUMN account_email")
        await conn.execute("DROP TABLE change_request_sync_events")
        for statement in _repair_statements():
            await conn.execute(statement)
        for statement in _repair_statements():
            await conn.execute(statement)
        column = await conn.fetchval(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'integration_settings' AND column_name = 'account_email'"
        )
        table_columns = await conn.fetchval(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = 'change_request_sync_events'"
        )
        index = await conn.fetchval(
            "SELECT count(*) FROM pg_indexes "
            "WHERE indexname = 'ix_change_request_sync_events_change_request_id'"
        )
        return column, table_columns, index
    finally:
        await transaction.rollback()
        await conn.close()


def test_the_repair_restores_what_the_baseline_defines_and_is_repeatable():
    column, table_columns, index = asyncio.run(_repair_on_a_pre_baseline_schema())

    assert column == 1
    assert table_columns == 10
    assert index == 1
