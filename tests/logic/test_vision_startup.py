"""Startup kind normalization keeps a Vision's kind and id."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.main as main
from app.core.database import Base
from app.models import Document, Project


async def test_a_restart_keeps_a_vision_and_still_repairs_an_unknown_kind(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        db.add(Project(id=1, name="Restart", prefix="RST"))
        await db.flush()
        db.add_all(
            [
                Document(project_id=1, doc_id="RST-VIS-001", doc_type="VIS", title="Vision"),
                Document(project_id=1, doc_id="RST-XYZ-001", doc_type="XYZ", title="Unknown"),
            ]
        )
        await db.commit()
    monkeypatch.setattr(main, "async_session_maker", maker)

    await main.normalize_document_kinds_and_ids()

    async with maker() as db:
        rows = (await db.execute(select(Document).order_by(Document.id))).scalars().all()
        assert [(row.doc_type, row.doc_id) for row in rows] == [
            ("VIS", "RST-VIS-001"),
            ("SPEC", "RST-SPEC-001"),
        ]
    await engine.dispose()
