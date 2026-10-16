"""Company logo: admin customer-logo storage, retrieval, and PDF rendering."""

import base64
import io

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.datastructures import Headers, UploadFile

from app.api.company_logo import delete_company_logo, get_company_logo, set_company_logo
from app.api.export import _load_report_logo, _requirements_pdf
from app.core.database import Base
from app.models import Project, Requirement
from app.models.user import User, UserRole

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        project = Project(name="Alpha", prefix="ALP")
        db.add(project)
        db.add(
            User(
                email="admin@test.local",
                full_name="Ada Admin",
                hashed_password="x",
                role=UserRole.admin,
            )
        )
        await db.flush()
        db.add(
            Requirement(
                project_id=project.id, req_id="ALP-REQ-001", title="Login", status="Approved"
            )
        )
        await db.commit()
        yield db
    await engine.dispose()


async def _admin(db):
    return (await db.execute(select(User).where(User.role == UserRole.admin))).scalar_one()


def _upload(data: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        io.BytesIO(data), filename="logo.png", headers=Headers({"content-type": content_type})
    )


async def test_set_get_delete_logo_roundtrip(session):
    admin = await _admin(session)
    out = await set_company_logo(file=_upload(PNG, "image/png"), db=session, current_user=admin)
    assert out["content_type"] == "image/png"
    assert out["size"] == len(PNG)

    resp = await get_company_logo(db=session, current_user=admin)
    assert resp.body == PNG
    assert resp.media_type == "image/png"
    assert await _load_report_logo(session) == PNG

    await delete_company_logo(db=session, current_user=admin)
    with pytest.raises(HTTPException) as exc:
        await get_company_logo(db=session, current_user=admin)
    assert exc.value.status_code == 404
    assert await _load_report_logo(session) is None


async def test_non_image_rejected(session):
    admin = await _admin(session)
    with pytest.raises(HTTPException) as exc:
        await set_company_logo(file=_upload(b"nope", "text/plain"), db=session, current_user=admin)
    assert exc.value.status_code == 415


async def test_requirements_pdf_embeds_logo_and_stays_valid(session):
    project = (await session.execute(select(Project))).scalars().first()
    reqs = (await session.execute(select(Requirement))).scalars().all()
    without = _requirements_pdf(project, list(reqs), None)
    withlogo = _requirements_pdf(project, list(reqs), PNG)
    assert without[:5] == b"%PDF-"
    assert withlogo[:5] == b"%PDF-"
    assert len(withlogo) >= len(without)
