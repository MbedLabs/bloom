"""Each artefact records internally who created it, and no response carries the record."""

import importlib
import io
import json
import pkgutil
from types import SimpleNamespace

import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

import app.api
import app.schemas
from app.api.attachments import publish_test_report
from app.api.campaigns import create_campaign
from app.api.changes import create_change_request
from app.api.defects import create_defect
from app.api.designs import create_design_item
from app.api.documents import create_document
from app.api.import_service import (
    ImportResult,
    _import_docs,
    import_markdown,
    import_test_cases_file,
    import_testrail,
)
from app.api.integrations import _new_defect_from_issue
from app.api.requirements import create_requirement
from app.api.risks import create_risk_item
from app.api.test_cases import create_test_case
from app.api.test_concepts import create_test_concept
from app.api.test_suites import create_suite
from app.api.users import delete_user
from app.core.database import Base
from app.models import Defect, Document, IntegrationSetting, Project, Requirement
from app.models import TestCase as CaseModel
from app.models import TestSuite as SuiteModel
from app.models.models import ARTEFACT_MODELS
from app.models.user import User, UserRole
from app.schemas import schemas


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        db.add_all([Project(name="Demo", prefix="PRJ"), Project(name="ABC", prefix="ABC")])
        for email, name in (("admin@test.local", "Ada Admin"), ("ann@test.local", "Ann Author")):
            db.add(User(email=email, full_name=name, hashed_password="x", role=UserRole.admin))
        await db.commit()
        yield db
    await engine.dispose()


async def _user(db, email):
    return (await db.execute(select(User).where(User.email == email))).scalar_one()


async def _creators(db, model):
    return (await db.execute(select(model.created_by_id))).scalars().all()


def _upload(content: bytes) -> UploadFile:
    return UploadFile(io.BytesIO(content))


async def test_every_create_route_records_the_actor(session):
    ann = await _user(session, "ann@test.local")
    session.add(Requirement(project_id=1, req_id="PRJ-REQ-900", title="Older"))
    await session.flush()

    await create_requirement(
        data=schemas.RequirementCreate(project_id=1, title="R"), db=session, current_user=ann
    )
    await create_test_case(
        data=schemas.TestCaseCreate(project_id=1, title="T"), db=session, current_user=ann
    )
    await create_document(
        project_id=1,
        data=schemas.DocumentCreate(project_id=1, title="S"),
        db=session,
        current_user=ann,
    )
    await create_suite(
        data=schemas.TestSuiteCreate(project_id=1, name="S"), db=session, current_user=ann
    )
    await create_campaign(
        data=schemas.TestCampaignCreate(project_id=1, name="C"), db=session, current_user=ann
    )
    await create_defect(
        data=schemas.DefectCreate(project_id=1, title="D"), db=session, current_user=ann
    )
    await create_design_item(
        data=schemas.DesignItemCreate(project_id=1, title="D"), db=session, current_user=ann
    )
    await create_risk_item(
        data=schemas.RiskItemCreate(project_id=1, title="R"), db=session, current_user=ann
    )
    await create_change_request(
        data=schemas.ChangeRequestCreate(project_id=1, title="C"), db=session, current_user=ann
    )
    await create_test_concept(
        data=schemas.TestConceptCreate(project_id=1, name="C"), db=session, current_user=ann
    )

    for model in ARTEFACT_MODELS:
        expected = [None, ann.id] if model is Requirement else [ann.id]
        assert await _creators(session, model) == expected, model.__name__


async def test_every_import_records_the_importer(session):
    ann = await _user(session, "ann@test.local")
    session.add(Requirement(project_id=2, req_id="ABC-REQ-001", title="Source"))
    await session.flush()
    alpha, beta = (await session.execute(select(Project).order_by(Project.id))).scalars().all()

    result = ImportResult(imported=0, skipped=0, new_ids=[], errors=[])
    await _import_docs(session, ann, "REQ", [1], beta, alpha, result)
    await import_test_cases_file(
        project_id=1,
        format="csv",
        file=_upload(b"tc_id,title\n,From CSV\n"),
        db=session,
        current_user=ann,
    )
    await import_testrail(
        project_id=1,
        format="xml",
        file=_upload(
            b"<suite><sections><section><name>Boot</name><cases><case><id>C1</id>"
            b"<title>From TestRail</title></case></cases></section></sections></suite>"
        ),
        mapping=None,
        db=session,
        current_user=ann,
    )
    await import_markdown(
        project_id=1,
        default_type=None,
        file=_upload(b"## [DES] From Markdown\nBody\n"),
        collision_actions=json.dumps({}),
        db=session,
        current_user=ann,
    )

    copied = (
        await session.execute(select(Requirement).where(Requirement.project_id == 1))
    ).scalar_one()
    assert copied.created_by_id == ann.id
    assert await _creators(session, CaseModel) == [ann.id, ann.id]
    assert await _creators(session, SuiteModel) == [ann.id]
    designs = [m for m in ARTEFACT_MODELS if m.__name__ == "DesignItem"][0]
    assert await _creators(session, designs) == [ann.id]


async def test_a_jira_defect_records_the_integration_account(session):
    ann = await _user(session, "ann@test.local")
    for project, email, expected in ((1, "ANN@test.local", ann.id), (2, "nobody@test.local", None)):
        setting = IntegrationSetting(project_id=project, tracker="jira", account_email=email)
        session.add(setting)
        await session.flush()
        defect = await _new_defect_from_issue(
            session, setting, "OPS", 7, {"summary": "Crash"}, event_type="pull"
        )
        assert (defect.created_by_id, defect.reporter_id) == (expected, expected)


async def test_a_bud_report_records_the_credential_owner(session):
    ann = await _user(session, "ann@test.local")
    for run_id, owner in ((41, ann.id), (42, None)):
        await publish_test_report(
            data=schemas.TestReportPublish(
                project_prefix="PRJ",
                bud_run_id=run_id,
                run_name="Nightly",
                total_tests=1,
                passed_tests=1,
                failed_tests=0,
                files=[],
            ),
            db=session,
            _service_credential=SimpleNamespace(created_by_user_id=owner),
        )
    reports = (await session.execute(select(Document).order_by(Document.id))).scalars().all()
    assert [r.created_by_id for r in reports] == [ann.id, None]


async def test_deleting_a_user_clears_the_record(session):
    admin = await _user(session, "admin@test.local")
    ann = await _user(session, "ann@test.local")
    await create_requirement(
        data=schemas.RequirementCreate(project_id=1, title="R"), db=session, current_user=ann
    )
    await create_defect(
        data=schemas.DefectCreate(project_id=1, title="D"), db=session, current_user=ann
    )

    await delete_user(user_id=ann.id, admin=admin, db=session)

    assert await _creators(session, Requirement) == [None]
    assert await _creators(session, Defect) == [None]


def test_no_response_model_carries_the_creator():
    carriers = []
    for package in (app.api, app.schemas):
        for info in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f"{package.__name__}.{info.name}")
            for value in vars(module).values():
                if isinstance(value, type) and issubclass(value, BaseModel):
                    if "created_by_id" in value.model_fields:
                        carriers.append(f"{module.__name__}.{value.__name__}")
    assert carriers == []
