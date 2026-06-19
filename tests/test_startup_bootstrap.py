from __future__ import annotations

import pytest

from app import main as main_module


@pytest.mark.asyncio
async def test_lifespan_skips_legacy_bootstrap_when_startup_repair_disabled(monkeypatch):
    calls: list[str] = []

    async def fake_create_tables():
        calls.append("create_tables")

    async def fake_migrate_user_columns():
        calls.append("migrate_user_columns")

    async def fake_normalize_document_kinds_and_ids():
        calls.append("normalize_document_kinds_and_ids")

    async def fake_backfill_campaign_public_ids():
        calls.append("backfill_campaign_public_ids")

    async def fake_normalize_non_document_public_ids():
        calls.append("normalize_non_document_public_ids")

    async def fake_seed_admin_user():
        calls.append("seed_admin_user")

    monkeypatch.setattr(main_module.settings, "RUN_STARTUP_DATA_REPAIR", False)
    monkeypatch.setattr(main_module, "create_tables", fake_create_tables)
    monkeypatch.setattr(main_module, "migrate_user_columns", fake_migrate_user_columns)
    monkeypatch.setattr(
        main_module,
        "normalize_document_kinds_and_ids",
        fake_normalize_document_kinds_and_ids,
    )
    monkeypatch.setattr(
        main_module, "backfill_campaign_public_ids", fake_backfill_campaign_public_ids
    )
    monkeypatch.setattr(
        main_module,
        "normalize_non_document_public_ids",
        fake_normalize_non_document_public_ids,
    )
    monkeypatch.setattr(main_module, "seed_admin_user", fake_seed_admin_user)

    async with main_module.lifespan(main_module.app):
        pass

    assert calls == []


@pytest.mark.asyncio
async def test_lifespan_runs_legacy_bootstrap_when_startup_repair_enabled(monkeypatch):
    calls: list[str] = []

    async def fake_create_tables():
        calls.append("create_tables")

    async def fake_migrate_user_columns():
        calls.append("migrate_user_columns")

    async def fake_normalize_document_kinds_and_ids():
        calls.append("normalize_document_kinds_and_ids")

    async def fake_backfill_campaign_public_ids():
        calls.append("backfill_campaign_public_ids")

    async def fake_normalize_non_document_public_ids():
        calls.append("normalize_non_document_public_ids")

    async def fake_seed_admin_user():
        calls.append("seed_admin_user")

    monkeypatch.setattr(main_module.settings, "RUN_STARTUP_DATA_REPAIR", True)
    monkeypatch.setattr(main_module, "create_tables", fake_create_tables)
    monkeypatch.setattr(main_module, "migrate_user_columns", fake_migrate_user_columns)
    monkeypatch.setattr(
        main_module,
        "normalize_document_kinds_and_ids",
        fake_normalize_document_kinds_and_ids,
    )
    monkeypatch.setattr(
        main_module, "backfill_campaign_public_ids", fake_backfill_campaign_public_ids
    )
    monkeypatch.setattr(
        main_module,
        "normalize_non_document_public_ids",
        fake_normalize_non_document_public_ids,
    )
    monkeypatch.setattr(main_module, "seed_admin_user", fake_seed_admin_user)

    async with main_module.lifespan(main_module.app):
        pass

    assert calls == [
        "create_tables",
        "migrate_user_columns",
        "normalize_document_kinds_and_ids",
        "backfill_campaign_public_ids",
        "normalize_non_document_public_ids",
        "seed_admin_user",
    ]
