"""Database-backed ReqIF rate and concurrency controls."""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.models import ImportAttempt, Project
from app.models.user import User, UserRole
from app.services.import_attempts import begin_import_attempt, finish_import_attempt


@pytest_asyncio.fixture
async def import_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        user = User(
            email="importer@example.com",
            full_name="Importer",
            hashed_password="hash",
            role=UserRole.admin,
            is_active=True,
        )
        project = Project(name="Import Project", prefix="IMP")
        session.add_all([user, project])
        await session.commit()
        await session.refresh(user)
        await session.refresh(project)
        yield session, user, project
    await engine.dispose()


@pytest.mark.asyncio
async def test_one_active_import_per_project(import_db):
    db, user, project = import_db
    first = await begin_import_attempt(db, user_id=user.id, project_id=project.id)
    first_id = first.id

    with pytest.raises(HTTPException) as error:
        await begin_import_attempt(db, user_id=user.id, project_id=project.id)

    assert error.value.status_code == 429
    await finish_import_attempt(db, first_id, "completed")


@pytest.mark.asyncio
async def test_five_import_starts_per_user_per_15_minutes(import_db, monkeypatch):
    db, user, project = import_db
    monkeypatch.setattr(settings, "REQIF_IMPORTS_PER_15_MINUTES", 2)
    for _ in range(2):
        attempt = await begin_import_attempt(db, user_id=user.id, project_id=project.id)
        await finish_import_attempt(db, attempt.id, "completed")

    with pytest.raises(HTTPException) as error:
        await begin_import_attempt(db, user_id=user.id, project_id=project.id)

    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "900"
    attempts = (await db.scalars(ImportAttempt.__table__.select())).all()
    assert len(attempts) == 2
