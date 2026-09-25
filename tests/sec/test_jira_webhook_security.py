"""Jira webhook: signature enforcement, replay protection, and status mapping."""

import hashlib
import hmac
import json

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import integrations
from app.core.database import Base, get_db
from app.models import (
    ChangeRequest,
    ChangeRequestSyncEvent,
    Defect,
    DefectSyncEvent,
    IntegrationSetting,
    Project,
)
from app.models import TestCase as TestCaseModel
from app.models.user import User, UserRole
from app.services.integration_secrets import encrypt_integration_secret

SECRET = "jira-hook-secret-123"


@pytest_asyncio.fixture
async def env():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as setup:
        project = Project(name="Alpha", prefix="ALP")
        setup.add(project)
        await setup.flush()
        setup.add(
            Defect(
                project_id=project.id,
                defect_id="ALP-DEF-001",
                title="Broken login",
                status="Open",
                external_tracker="jira",
                external_repo_full_name="PROJ",
                external_issue_number=42,
            )
        )
        setup.add(
            ChangeRequest(
                project_id=project.id,
                change_id="ALP-CR-001",
                title="Swap the sensor",
                status="Submitted",
                external_tracker="jira",
                external_repo_full_name="PROJ",
                external_issue_number=99,
            )
        )
        setup.add(
            IntegrationSetting(
                project_id=project.id,
                tracker="jira",
                base_url="https://acme.atlassian.net",
                account_email="bot@acme.test",
                webhook_secret=encrypt_integration_secret(SECRET),
                enabled=True,
            )
        )
        await setup.commit()

    app = FastAPI()
    app.include_router(integrations.router, prefix="/api/integrations")

    async def override_get_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, maker
    await engine.dispose()


def _payload(
    issue_key: str,
    category: str = "done",
    status_name: str = "Done",
    summary: str = "Imported issue",
    event: str = "jira:issue_updated",
) -> bytes:
    return json.dumps(
        {
            "webhookEvent": event,
            "issue": {
                "key": issue_key,
                "fields": {
                    "summary": summary,
                    "issuetype": {"name": "Bug"},
                    "status": {"name": status_name, "statusCategory": {"key": category}},
                },
            },
        }
    ).encode()


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def _post(client, body: bytes, *, signature=None, delivery="d-1"):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Hub-Signature"] = signature
    if delivery is not None:
        headers["X-Atlassian-Webhook-Identifier"] = delivery
    return client.post("/api/integrations/jira/webhook", content=body, headers=headers)


async def _defect_status(maker) -> str:
    async with maker() as session:
        row = (
            await session.execute(select(Defect).where(Defect.defect_id == "ALP-DEF-001"))
        ).scalar_one()
        return row.status


async def _change_status(maker) -> str:
    async with maker() as session:
        row = (
            await session.execute(
                select(ChangeRequest).where(ChangeRequest.change_id == "ALP-CR-001")
            )
        ).scalar_one()
        return row.status


def test_rejects_missing_signature(env):
    """Omitting the header must not bypass verification."""
    client, _ = env
    response = _post(client, _payload("PROJ-42"), signature=None)
    assert response.status_code == 403


def test_rejects_wrong_signature(env):
    client, _ = env
    response = _post(client, _payload("PROJ-42"), signature="sha256=deadbeef")
    assert response.status_code == 403


def test_rejects_signature_over_different_body(env):
    """A signature lifted from another delivery must not validate."""
    client, _ = env
    response = _post(client, _payload("PROJ-42"), signature=_sign(_payload("PROJ-999")))
    assert response.status_code == 403


def test_requires_a_delivery_identifier(env):
    client, _ = env
    body = _payload("PROJ-42")
    response = _post(client, body, signature=_sign(body), delivery=None)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_valid_signature_closes_the_linked_defect(env):
    client, maker = env
    body = _payload("PROJ-42")

    response = _post(client, body, signature=_sign(body))

    assert response.status_code == 200
    assert response.json()["target"] == "defect"
    assert await _defect_status(maker) == "Closed"


@pytest.mark.asyncio
async def test_valid_signature_closes_the_linked_change_request(env):
    client, maker = env
    body = _payload("PROJ-99")

    response = _post(client, body, signature=_sign(body), delivery="d-cr")

    assert response.status_code == 200
    assert response.json()["target"] == "change_request"
    assert await _change_status(maker) == "Closed"


@pytest.mark.asyncio
async def test_status_category_maps_to_bloom_status(env):
    client, maker = env
    body = _payload("PROJ-42", category="indeterminate", status_name="In Review")

    assert _post(client, body, signature=_sign(body)).status_code == 200
    assert await _defect_status(maker) == "In Progress"


@pytest.mark.asyncio
async def test_replayed_delivery_is_ignored(env):
    """The same delivery id must apply once, so a captured request cannot be replayed."""
    client, maker = env
    body = _payload("PROJ-42")
    assert _post(client, body, signature=_sign(body), delivery="same").status_code == 200

    # Flip the defect back, then replay the identical signed request.
    async with maker() as session:
        row = (
            await session.execute(select(Defect).where(Defect.defect_id == "ALP-DEF-001"))
        ).scalar_one()
        row.status = "Open"
        await session.commit()

    replay = _post(client, body, signature=_sign(body), delivery="same")

    assert replay.json()["status"] == "duplicate"
    assert await _defect_status(maker) == "Open"


def test_unlinked_issue_is_not_found(env):
    client, _ = env
    body = _payload("PROJ-777")
    assert _post(client, body, signature=_sign(body)).status_code == 404


def test_non_issue_events_are_ignored(env):
    client, _ = env
    body = json.dumps({"webhookEvent": "jira:worklog_updated"}).encode()
    response = _post(client, body, signature=_sign(body))
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_malformed_issue_key_is_ignored(env):
    client, _ = env
    body = _payload("NOTAKEY")
    response = _post(client, body, signature=_sign(body))
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_rejected_delivery_records_no_successful_event(env):
    """A spoofed delivery must leave no successful sync event on either log."""
    client, maker = env
    _post(client, _payload("PROJ-42"), signature="sha256=bad")
    _post(client, _payload("PROJ-99"), signature="sha256=bad", delivery="d-cr")

    async with maker() as session:
        defect_events = (await session.execute(select(DefectSyncEvent))).scalars().all()
        change_events = (await session.execute(select(ChangeRequestSyncEvent))).scalars().all()

    assert [e for e in defect_events if e.success] == []
    assert [e for e in change_events if e.success] == []


@pytest.mark.asyncio
async def test_sync_events_route_to_the_matching_log(env):
    """Defect events and change-request events must land in their own tables."""
    _, maker = env
    async with maker() as session:
        integrations._log_target_sync_event(session, "defect", 1, "inbound", "jira", "probe_defect")
        integrations._log_target_sync_event(
            session, "change_request", 1, "inbound", "jira", "probe_change"
        )
        await session.commit()

    async with maker() as session:
        defect_events = (await session.execute(select(DefectSyncEvent))).scalars().all()
        change_events = (await session.execute(select(ChangeRequestSyncEvent))).scalars().all()

    assert [e.event_type for e in defect_events] == ["probe_defect"]
    assert [e.event_type for e in change_events] == ["probe_change"]


async def _map_project_for_creation(maker, *, create: bool) -> None:
    async with maker() as session:
        setting = (
            await session.execute(
                select(IntegrationSetting).where(IntegrationSetting.tracker == "jira")
            )
        ).scalar_one()
        setting.jira_project_key = "PROJ"
        setting.create_defects_on_inbound = create
        await session.commit()


@pytest.mark.asyncio
async def test_inbound_creates_a_defect_when_the_project_is_mapped(env):
    """An inbound Jira issue with no matching defect creates one for the mapped project."""
    client, maker = env
    await _map_project_for_creation(maker, create=True)

    body = _payload("PROJ-500", category="new", status_name="To Do", summary="Sensor fails")
    response = _post(client, body, signature=_sign(body), delivery="create-1")

    assert response.status_code == 200
    assert response.json()["status"] == "created"
    assert response.json()["target"] == "defect"
    async with maker() as session:
        defect = (
            await session.execute(
                select(Defect).where(
                    Defect.external_tracker == "jira",
                    Defect.external_repo_full_name == "PROJ",
                    Defect.external_issue_number == 500,
                )
            )
        ).scalar_one()
        assert defect.title == "Sensor fails"
        assert defect.status == "Open"


@pytest.mark.asyncio
async def test_inbound_creation_is_idempotent_on_replay(env):
    """A replayed create delivery does not make a second defect."""
    client, maker = env
    await _map_project_for_creation(maker, create=True)
    body = _payload("PROJ-501")
    assert _post(client, body, signature=_sign(body), delivery="dup").status_code == 200
    replay = _post(client, body, signature=_sign(body), delivery="dup")
    assert replay.json()["status"] == "duplicate"
    async with maker() as session:
        rows = (
            (await session.execute(select(Defect).where(Defect.external_issue_number == 501)))
            .scalars()
            .all()
        )
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_inbound_does_not_create_when_disabled(env):
    """With creation disabled, an unmatched issue is rejected even if the project maps."""
    client, maker = env
    await _map_project_for_creation(maker, create=False)
    body = _payload("PROJ-502")
    assert _post(client, body, signature=_sign(body), delivery="off-1").status_code == 404


def _issue_payload(issue_key, event="jira:issue_created", **fields):
    base = {
        "summary": "Sensor fails",
        "issuetype": {"name": "Bug"},
        "status": {"name": "To Do", "statusCategory": {"key": "new"}},
    }
    base.update(fields)
    return json.dumps({"webhookEvent": event, "issue": {"key": issue_key, "fields": base}}).encode()


@pytest.mark.asyncio
async def test_created_defect_copies_the_issue(env):
    """Description, priority, severity, URL and the named test case come from the issue."""
    client, maker = env
    await _map_project_for_creation(maker, create=True)
    async with maker() as session:
        session.add(TestCaseModel(project_id=1, tc_id="ALP-TC-004", title="Boot"))
        bot = User(
            email="Bot@Acme.test",
            full_name="Jira bot",
            hashed_password="x",
            role=UserRole.maintainer,
        )
        session.add(bot)
        await session.commit()
    description = {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "See ALP-TC-004"}]}],
    }
    body = _issue_payload("PROJ-600", description=description, priority={"name": "Highest"})
    assert (
        _post(client, body, signature=_sign(body), delivery="c-600").json()["status"] == "created"
    )
    async with maker() as session:
        defect = (
            await session.execute(select(Defect).where(Defect.external_issue_number == 600))
        ).scalar_one()
        test_case = (await session.execute(select(TestCaseModel))).scalar_one()
    assert defect.description == "See ALP-TC-004"
    assert (defect.priority, defect.severity) == ("Critical", "Critical")
    assert defect.external_issue_url == "https://acme.atlassian.net/browse/PROJ-600"
    assert (defect.source_type, defect.source_id) == ("TC", test_case.id)
    assert defect.external_issue_state == "To Do"
    assert defect.reporter_id == bot.id


@pytest.mark.asyncio
async def test_issues_outside_the_filter_are_ignored(env):
    client, maker = env
    await _map_project_for_creation(maker, create=True)
    task = _issue_payload("PROJ-601", issuetype={"name": "Task"})
    assert _post(client, task, signature=_sign(task), delivery="t-1").json()["status"] == "ignored"
    async with maker() as session:
        setting = (await session.execute(select(IntegrationSetting))).scalar_one()
        setting.jira_label = "bench"
        await session.commit()
    unlabelled = _issue_payload("PROJ-602")
    assert _post(client, unlabelled, signature=_sign(unlabelled), delivery="t-2").json() == {
        "status": "ignored",
        "reason": "issue not taken in by this project",
    }
    labelled = _issue_payload("PROJ-603", labels=["bench"])
    assert (
        _post(client, labelled, signature=_sign(labelled), delivery="t-3").json()["status"]
        == "created"
    )
    async with maker() as session:
        created = (
            await session.execute(select(Defect).where(Defect.external_issue_number == 603))
        ).scalar_one()
    assert created.reporter_id is None
    gone = _issue_payload("PROJ-604", event="jira:issue_deleted")
    assert _post(client, gone, signature=_sign(gone), delivery="t-4").json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_linked_defect_follows_the_issue_and_closes_on_resolution(env):
    client, maker = env
    body = _issue_payload(
        "PROJ-42",
        event="jira:issue_updated",
        summary="Login broken on reset",
        description="Steps in the log",
        priority={"name": "Low"},
    )
    assert (
        _post(client, body, signature=_sign(body), delivery="u-1").json()["status"] == "processed"
    )
    async with maker() as session:
        defect = (await session.execute(select(Defect))).scalar_one()
    assert (defect.title, defect.description, defect.priority) == (
        "Login broken on reset",
        "Steps in the log",
        "Low",
    )
    assert defect.status == "Open"
    assert defect.external_issue_url == "https://acme.atlassian.net/browse/PROJ-42"

    resolved = _issue_payload(
        "PROJ-42",
        event="jira:issue_updated",
        status={"name": "In Review", "statusCategory": {"key": "indeterminate"}},
        resolution={"name": "Fixed"},
    )
    _post(client, resolved, signature=_sign(resolved), delivery="u-2")
    async with maker() as session:
        defect = (await session.execute(select(Defect))).scalar_one()
    assert defect.status == "Closed" and defect.closed_at is not None


@pytest.mark.asyncio
async def test_deleted_issue_keeps_the_defect(env):
    client, maker = env
    body = _issue_payload("PROJ-42", event="jira:issue_deleted")
    assert (
        _post(client, body, signature=_sign(body), delivery="x-1").json()["status"] == "processed"
    )
    async with maker() as session:
        defect = (await session.execute(select(Defect))).scalar_one()
        change = (await session.execute(select(ChangeRequest))).scalar_one()
    assert defect.external_issue_state == "Removed in Jira"
    assert defect.title == "Broken login"
    gone = _issue_payload("PROJ-99", event="jira:issue_deleted")
    _post(client, gone, signature=_sign(gone), delivery="x-2")
    async with maker() as session:
        change = (await session.execute(select(ChangeRequest))).scalar_one()
    assert change.external_issue_state == "Removed in Jira"


@pytest.mark.asyncio
async def test_push_to_jira_only_when_two_way(env, monkeypatch):
    _, maker = env
    pushed = []

    async def fake_push(target, setting, changed):
        pushed.append(target.id)

    monkeypatch.setattr(integrations, "_push_to_jira", fake_push)
    async with maker() as session:
        setting = (await session.execute(select(IntegrationSetting))).scalar_one()
        setting.token_encrypted = encrypt_integration_secret("api-token")
        await session.commit()
    async with maker() as session:
        defect = (await session.execute(select(Defect))).scalar_one()
        change = (await session.execute(select(ChangeRequest))).scalar_one()
        await integrations.sync_defect_to_tracker(session, defect, {"title": "x"})
        await integrations.sync_change_request_to_tracker(session, change, {"title": "x"})
        assert pushed == []
        setting = (await session.execute(select(IntegrationSetting))).scalar_one()
        setting.two_way = True
        await session.flush()
        await integrations.sync_defect_to_tracker(session, defect, {"title": "x"})
        await integrations.sync_change_request_to_tracker(session, change, {"title": "x"})
    assert pushed == [defect.id, change.id]


def _search_transport(pages, seen, hosts=None):
    """A Jira that accepts the credential on the site and answers searches page by page."""

    def handler(request):
        if request.url.path.endswith("/rest/api/3/myself"):
            return httpx.Response(200, json={"accountId": "acc"})
        if hosts is not None:
            hosts.append(str(request.url))
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=pages[len(seen) - 1])

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_pull_creates_the_missing_defects(env, monkeypatch):
    _, maker = env
    await _map_project_for_creation(maker, create=True)
    seen = []
    pages = [
        {
            "issues": [
                {"key": "PROJ-42", "fields": {"issuetype": {"name": "Bug"}, "summary": "linked"}},
                {"key": "PROJ-700", "fields": {"issuetype": {"name": "Bug"}, "summary": "new"}},
            ],
            "nextPageToken": "p2",
            "isLast": False,
        },
        {
            "issues": [
                {"key": "PROJ-701", "fields": {"issuetype": {"name": "Task"}}},
                {"key": "bad", "fields": {"issuetype": {"name": "Bug"}}},
            ],
            "isLast": True,
        },
    ]
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        integrations.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=_search_transport(pages, seen), **kw),
    )
    async with maker() as session:
        setting = (await session.execute(select(IntegrationSetting))).scalar_one()
        setting.token_encrypted = encrypt_integration_secret("api-token")
        admin = User(email="a@acme.test", full_name="Ada", hashed_password="x", role=UserRole.admin)
        session.add(admin)
        await session.flush()
        result = await integrations.pull_jira_issues(setting.id, db=session, current_user=admin)
        await session.commit()
    assert (result.searched, result.created, result.already_linked, result.skipped) == (4, 1, 1, 2)
    assert result.new_ids == ["ALP-DEF-002"]
    assert seen[0]["jql"] == (
        'project = "PROJ" AND issuetype in ("Bug") AND statusCategory != Done ORDER BY created ASC'
    )
    assert seen[1]["nextPageToken"] == "p2"
    async with maker() as session:
        pulled = (
            await session.execute(select(Defect).where(Defect.external_issue_number == 700))
        ).scalar_one()
        event = (
            await session.execute(
                select(DefectSyncEvent).where(DefectSyncEvent.defect_id == pulled.id)
            )
        ).scalar_one()
    assert event.event_type == "pulled"


@pytest.mark.asyncio
async def test_pull_reports_what_it_needs_and_jira_errors(env, monkeypatch):
    _, maker = env
    async with maker() as session:
        setting = (await session.execute(select(IntegrationSetting))).scalar_one()
        admin = User(email="b@acme.test", full_name="Bo", hashed_password="x", role=UserRole.admin)
        session.add(admin)
        await session.flush()
        with pytest.raises(HTTPException) as missing:
            await integrations.pull_jira_issues(setting.id, db=session, current_user=admin)
        assert missing.value.status_code == 400
        with pytest.raises(HTTPException) as unknown:
            await integrations.pull_jira_issues(999, db=session, current_user=admin)
        assert unknown.value.status_code == 404

        setting.jira_project_key = "PROJ"
        setting.token_encrypted = encrypt_integration_secret("api-token")
        await session.flush()
        real_client = httpx.AsyncClient
        monkeypatch.setattr(
            integrations.httpx,
            "AsyncClient",
            lambda **kw: real_client(
                transport=httpx.MockTransport(lambda request: httpx.Response(401)), **kw
            ),
        )
        with pytest.raises(HTTPException) as refused:
            await integrations.pull_jira_issues(setting.id, db=session, current_user=admin)
        assert refused.value.status_code == 400
        assert refused.value.detail.startswith("Jira did not accept the account email")

        def unreachable(request):
            raise httpx.ConnectError("no route", request=request)

        monkeypatch.setattr(
            integrations.httpx,
            "AsyncClient",
            lambda **kw: real_client(transport=httpx.MockTransport(unreachable), **kw),
        )
        with pytest.raises(HTTPException) as down:
            await integrations.pull_jira_issues(setting.id, db=session, current_user=admin)
        assert down.value.status_code == 502
        assert down.value.detail.startswith("Jira is unreachable")


def test_filter_validation():
    integrations._validate_jira_filter(["Bug"], {"Highest": "Critical"})
    with pytest.raises(HTTPException):
        integrations._validate_jira_filter([" "], None)
    with pytest.raises(HTTPException) as bad:
        integrations._validate_jira_filter(None, {"Highest": "Urgent"})
    assert "Urgent" in bad.value.detail


@pytest.mark.asyncio
async def test_a_scoped_token_is_used_through_the_atlassian_gateway(env, monkeypatch):
    _, maker = env
    await _map_project_for_creation(maker, create=True)
    calls = []

    def handler(request):
        url = str(request.url)
        calls.append(url)
        if url.endswith("/_edge/tenant_info"):
            return httpx.Response(200, json={"cloudId": "cloud-1"})
        if url.startswith("https://api.atlassian.com/ex/jira/cloud-1/"):
            if request.url.path.endswith("/myself"):
                return httpx.Response(200, json={"accountId": "acc"})
            return httpx.Response(
                200,
                json={
                    "issues": [
                        {
                            "key": "PROJ-800",
                            "fields": {"issuetype": {"name": "Bug"}, "summary": "s"},
                        }
                    ],
                    "isLast": True,
                },
            )
        return httpx.Response(401)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        integrations.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    async with maker() as session:
        setting = (await session.execute(select(IntegrationSetting))).scalar_one()
        setting.token_encrypted = encrypt_integration_secret("scoped-token")
        admin = User(email="c@acme.test", full_name="Cy", hashed_password="x", role=UserRole.admin)
        session.add(admin)
        await session.flush()
        result = await integrations.pull_jira_issues(setting.id, db=session, current_user=admin)
        await session.commit()
        site = setting.base_url.rstrip("/")
    assert result.created == 1
    search = [c for c in calls if c.endswith("/rest/api/3/search/jql")]
    assert search == ["https://api.atlassian.com/ex/jira/cloud-1/rest/api/3/search/jql"]
    async with maker() as session:
        pulled = (
            await session.execute(select(Defect).where(Defect.external_issue_number == 800))
        ).scalar_one()
    assert pulled.external_issue_url == f"{site}/browse/PROJ-800"
