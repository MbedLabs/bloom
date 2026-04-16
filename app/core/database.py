"""
Database connection and session management.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from typing import AsyncGenerator

from app.core.config import settings


DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE requirements ADD COLUMN IF NOT EXISTS reviewer_id INTEGER"))
        await conn.execute(text("ALTER TABLE requirements ADD COLUMN IF NOT EXISTS approver_id INTEGER"))
        await conn.execute(text("ALTER TABLE requirements ADD COLUMN IF NOT EXISTS reviewed_by_id INTEGER"))
        await conn.execute(text("ALTER TABLE requirements ADD COLUMN IF NOT EXISTS approved_by_id INTEGER"))
        await conn.execute(text("ALTER TABLE requirements ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP"))
        await conn.execute(text("ALTER TABLE requirements ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP"))

        await conn.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS reviewer_id INTEGER"))
        await conn.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS approver_id INTEGER"))
        await conn.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS reviewed_by_id INTEGER"))
        await conn.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS approved_by_id INTEGER"))
        await conn.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP"))
        await conn.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP"))

        await conn.execute(text("ALTER TABLE test_campaigns ADD COLUMN IF NOT EXISTS configuration_id INTEGER"))
        await conn.execute(text("ALTER TABLE test_campaigns ADD COLUMN IF NOT EXISTS suite_id INTEGER"))
        await conn.execute(text("ALTER TABLE test_campaigns ADD COLUMN IF NOT EXISTS bud_run_id INTEGER"))
        await conn.execute(text("ALTER TABLE test_campaigns ADD COLUMN IF NOT EXISTS bud_run_url VARCHAR(500)"))
        await conn.execute(text("ALTER TABLE test_campaigns ADD COLUMN IF NOT EXISTS bud_run_status VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE test_campaigns ADD COLUMN IF NOT EXISTS started_at TIMESTAMP"))
        await conn.execute(text("ALTER TABLE test_campaigns ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP"))

        await conn.execute(text("ALTER TABLE test_campaign_items ADD COLUMN IF NOT EXISTS comment TEXT"))
        await conn.execute(text("ALTER TABLE test_campaign_items ADD COLUMN IF NOT EXISTS executed_at TIMESTAMP"))

        await conn.execute(text("CREATE TABLE IF NOT EXISTS project_variables (id SERIAL PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id), kind VARCHAR(20) NOT NULL DEFAULT 'variable', key VARCHAR(100) NOT NULL, value TEXT NOT NULL, description TEXT, created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(), updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW())"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_project_variable_kind_key ON project_variables(project_id, kind, key)"))

        for tbl in ("requirements", "test_cases", "design_items", "risk_items", "change_requests", "test_concepts", "documents"):
            await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS content_json JSONB"))
            await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS content_html TEXT"))
            await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS source_ref VARCHAR(100)"))
            await conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS source_project_id INTEGER"))

        await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS doc_id VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE baselines ADD COLUMN IF NOT EXISTS baseline_id VARCHAR(50)"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.

    Yields:
        AsyncSession: Database session.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
