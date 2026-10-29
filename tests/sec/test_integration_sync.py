"""Scheduled tracker sync: Jira creation, updates and deletions, GitHub and GitLab state,
failures, claiming, Sync now and the lifespan task."""

import asyncio
import json
from datetime import datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import main
from app.api import integrations
from app.core.database import Base
from app.models import (
    ChangeRequest,
    ChangeRequestSyncEvent,
    Defect,
    DefectSyncEvent,
    IntegrationSetting,
    Project,
)
from app.models.user import User, UserRole
from app.services import integration_sync
from app.services.integration_secrets import encrypt_integration_secret

NOW = datetime(2026, 10, 26, 12, 0, 0)
LATER = NOW + timedelta(minutes=16)
REAL_CLIENT = httpx.AsyncClient


@pytest_asyncio.fixture
async def maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _serve(monkeypatch, handler):
    """Answer every tracker call of the code under test with ``handler``."""
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), **kw),
    )


async def _project(maker, prefix: str = "PRJ") -> int:
    async with maker() as db:
        project = Project(name=f"Project {prefix}", prefix=prefix)
        db.add(project)
        await db.commit()
        return project.id


async def _setting(maker, project_id: int, tracker: str = "jira", **fields) -> int:
    values = {
        "project_id": project_id,
        "tracker": tracker,
        "token_encrypted": encrypt_integration_secret("api-token"),
        "enabled": True,
        "created_at": NOW - timedelta(days=1),
        "updated_at": NOW - timedelta(days=1),
    }
    if tracker == "jira":
        values.update(
            base_url="https://acme.atlassian.net",
            account_email="bot@acme.test",
            jira_project_key="PROJ",
        )
    values.update(fields)
    async with maker() as db:
        setting = IntegrationSetting(**values)
        db.add(setting)
        await db.commit()
        return setting.id


async def _defect(maker, project_id, tracker, repo, number, **fields) -> int:
    async with maker() as db:
        count = await db.scalar(select(func.count(Defect.id)))
        defect = Defect(
            project_id=project_id,
            defect_id=f"PRJ-DEF-{count + 101:03d}",
            title=fields.pop("title", "Linked"),
            status=fields.pop("status", "Open"),
            external_tracker=tracker,
            external_repo_full_name=repo,
            external_issue_number=number,
            **fields,
        )
        db.add(defect)
        await db.commit()
        return defect.id


async def _change(maker, project_id, tracker, repo, number, status="Submitted") -> int:
    async with maker() as db:
        count = await db.scalar(select(func.count(ChangeRequest.id)))
        change = ChangeRequest(
            project_id=project_id,
            change_id=f"PRJ-CR-{count + 101:03d}",
            title="Change",
            status=status,
            external_tracker=tracker,
            external_repo_full_name=repo,
            external_issue_number=number,
        )
        db.add(change)
        await db.commit()
        return change.id


async def _get(maker, model, row_id):
    async with maker() as db:
        return await db.get(model, row_id)


def _issue(key, *, kind="Bug", category="new", status="To Do", **fields) -> dict:
    return {
        "key": key,
        "fields": {
            "issuetype": {"name": kind},
            "status": {"name": status, "statusCategory": {"key": category}},
            "summary": fields.pop("summary", key),
            **fields,
        },
    }


class FakeJira:
    """A Jira site answering searches by kind and issue reads by status code."""

    def __init__(self, creation=(), changed=(), issue_status=None):
        self.creation = list(creation)
        self.changed = list(changed)
        self.issue_status = issue_status or {}
        self.jql: list[str] = []
        self.reads: list[str] = []

    def __call__(self, request):
        path = request.url.path
        if path.endswith("/rest/api/3/myself"):
            return httpx.Response(200, json={"accountId": "acc"})
        if request.method == "POST" and path.endswith("/rest/api/3/search/jql"):
            jql = json.loads(request.content)["jql"]
            self.jql.append(jql)
            issues = self.creation if "statusCategory != Done" in jql else self.changed
            return httpx.Response(200, json={"issues": issues, "isLast": True})
        if request.method == "GET" and "/rest/api/3/issue/" in path:
            key = path.rsplit("/", 1)[1]
            self.reads.append(key)
            return httpx.Response(self.issue_status.get(key, 200), json={"fields": {}})
        return httpx.Response(500)


async def _events(maker, model=DefectSyncEvent):
    async with maker() as db:
        return (await db.scalars(select(model).order_by(model.id))).all()


@pytest.mark.asyncio
async def test_first_run_creates_the_backlog_and_clears_the_full_scan(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(maker, project)
    await _defect(maker, project, "jira", "PROJ", 42)
    jira = FakeJira(creation=[_issue("PROJ-1"), _issue("PROJ-42"), _issue("PROJ-3", kind="Task")])
    _serve(monkeypatch, jira)

    assert await integration_sync.run_due(15, maker=maker, now=NOW) == [setting_id]

    creation_jql = [q for q in jira.jql if "statusCategory != Done" in q]
    assert creation_jql == [
        'project = "PROJ" AND issuetype in ("Bug") AND statusCategory != Done ORDER BY created ASC'
    ]
    async with maker() as db:
        created = (await db.scalars(select(Defect).where(Defect.external_issue_number == 1))).one()
        assert await db.scalar(select(func.count(Defect.id))) == 2
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.sync_full_scan is False
    assert (setting.synced_at, setting.sync_checked_at) == (NOW, NOW)
    assert (setting.sync_created, setting.sync_updated, setting.sync_error) == (1, 0, None)
    events = [e for e in await _events(maker) if e.defect_id == created.id]
    assert [(e.event_type, e.payload_summary) for e in events] == [
        ("synced", "created from PROJ-1")
    ]


@pytest.mark.asyncio
async def test_later_runs_search_the_window_and_follow_linked_targets(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(
        maker, project, sync_full_scan=False, synced_at=NOW - timedelta(minutes=20)
    )
    defect_id = await _defect(maker, project, "jira", "PROJ", 42, title="Old")
    change_id = await _change(maker, project, "jira", "PROJ", 99)
    jira = FakeJira(
        changed=[
            _issue(
                "PROJ-42",
                category="done",
                status="Done",
                summary="New title",
                description="Steps",
                priority={"name": "High"},
                resolution={"name": "Done"},
            ),
            _issue("PROJ-99", category="done", status="Done"),
        ]
    )
    _serve(monkeypatch, jira)

    await integration_sync.run_due(15, maker=maker, now=NOW)

    assert "statusCategory != Done AND updated >= -25m ORDER BY created ASC" in jira.jql[0]
    assert jira.jql[1] == 'project = "PROJ" AND updated >= -25m ORDER BY updated ASC'
    defect = await _get(maker, Defect, defect_id)
    assert (defect.status, defect.title, defect.priority) == ("Closed", "New title", "High")
    assert (defect.description, defect.external_issue_state) == ("Steps", "Done")
    change = await _get(maker, ChangeRequest, change_id)
    assert change.status == "Closed"
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.sync_updated == 2
    assert [e.event_type for e in await _events(maker)] == ["synced"]
    assert [e.event_type for e in await _events(maker, ChangeRequestSyncEvent)] == ["synced"]


@pytest.mark.asyncio
async def test_creation_off_creates_nothing_and_still_updates(maker, monkeypatch):
    project = await _project(maker)
    await _setting(maker, project, create_defects_on_inbound=False)
    defect_id = await _defect(maker, project, "jira", "PROJ", 42)
    jira = FakeJira(
        creation=[_issue("PROJ-1")],
        changed=[_issue("PROJ-42", category="done", status="Done")],
    )
    _serve(monkeypatch, jira)

    await integration_sync.run_due(15, maker=maker, now=NOW)

    assert not [q for q in jira.jql if "statusCategory != Done" in q]
    async with maker() as db:
        assert await db.scalar(select(func.count(Defect.id))) == 1
    assert (await _get(maker, Defect, defect_id)).status == "Closed"


@pytest.mark.asyncio
async def test_saving_the_setting_asks_for_a_full_scan_again(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(maker, project)
    _serve(monkeypatch, FakeJira())
    await integration_sync.run_due(15, maker=maker, now=NOW)
    assert (await _get(maker, IntegrationSetting, setting_id)).sync_full_scan is False

    async with maker() as db:
        admin = User(email="a@acme.test", full_name="Ada", hashed_password="x", role=UserRole.admin)
        db.add(admin)
        await db.flush()
        await integrations.update_integration_setting(
            setting_id,
            integrations.IntegrationSettingUpdate(jira_label="triage"),
            db=db,
            current_user=admin,
        )
        await db.commit()

    setting = await _get(maker, IntegrationSetting, setting_id)
    assert (setting.sync_full_scan, setting.sync_scan_from) == (True, None)


@pytest.mark.asyncio
async def test_a_save_during_a_full_scan_keeps_the_rescan(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(maker, project)
    original = integration_sync._fetch_jira

    async def fetch(setting, **kw):
        fetched = await original(setting, **kw)
        async with maker() as db:
            row = await db.get(IntegrationSetting, setting_id)
            row.jira_label = "triage"
            row.updated_at = NOW + timedelta(seconds=1)
            await db.commit()
        return fetched

    monkeypatch.setattr(integration_sync, "_fetch_jira", fetch)
    _serve(monkeypatch, FakeJira())

    await integration_sync.run_due(15, maker=maker, now=NOW)

    setting = await _get(maker, IntegrationSetting, setting_id)
    assert (setting.synced_at, setting.sync_full_scan) == (NOW, True)


@pytest.mark.asyncio
async def test_deleted_issues_are_marked_removed_and_the_cursor_moves(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(maker, project, create_defects_on_inbound=False)
    defect_id = await _defect(maker, project, "jira", "PROJ", 42)
    change_id = await _change(maker, project, "jira", "PROJ", 99)
    monkeypatch.setattr(integration_sync, "REMOVAL_CHECKS", 1)
    jira = FakeJira(issue_status={"PROJ-42": 404, "PROJ-99": 403})
    _serve(monkeypatch, jira)

    await integration_sync.run_due(15, maker=maker, now=NOW)
    assert jira.reads == ["PROJ-42"]
    assert (await _get(maker, Defect, defect_id)).external_issue_state == "Removed in Jira"
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert (setting.sync_removal_cursor, setting.sync_updated) == (42, 1)
    assert [e.payload_summary for e in await _events(maker)] == ["removed in tracker"]

    await integration_sync.run_due(15, maker=maker, now=LATER)
    assert jira.reads == ["PROJ-42", "PROJ-99"]
    assert (await _get(maker, ChangeRequest, change_id)).external_issue_state is None
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert (setting.sync_removal_cursor, setting.sync_error) == (99, None)


@pytest.mark.asyncio
async def test_capped_searches_continue_on_the_next_run(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(maker, project)
    monkeypatch.setattr(integrations, "MAX_PULLED_ISSUES", 2)
    monkeypatch.setattr(integration_sync, "MAX_PULLED_ISSUES", 2)
    jira = FakeJira(
        creation=[
            _issue("PROJ-1", created="2026-10-20T10:00:00.000+0000"),
            _issue("PROJ-2", created="2026-10-21T10:00:00.000+0200"),
        ],
        changed=[
            _issue("PROJ-1", updated="2026-10-26T09:00:00.000+0000"),
            _issue("PROJ-2", updated="2026-10-26T10:30:00.000+0100"),
        ],
    )
    _serve(monkeypatch, jira)

    await integration_sync.run_due(15, maker=maker, now=NOW)
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.sync_full_scan is True
    assert setting.sync_scan_from == datetime(2026, 10, 21, 8, 0)
    assert setting.synced_at == datetime(2026, 10, 26, 9, 30)

    await integration_sync.run_due(15, maker=maker, now=LATER)
    creation_jql = [q for q in jira.jql if "statusCategory != Done" in q]
    assert "created >= -" in creation_jql[1] and "updated >=" not in creation_jql[1]


async def _github(maker, **fields):
    project = await _project(maker, fields.pop("prefix", "GHB"))
    setting_id = await _setting(maker, project, fields.pop("tracker", "github"), **fields)
    return project, setting_id


@pytest.mark.asyncio
async def test_github_issue_state_reaches_defects_and_change_requests(maker, monkeypatch):
    project, setting_id = await _github(maker)
    defect_id = await _defect(maker, project, "github", "acme/app", 5)
    change_id = await _change(maker, project, "github", "acme/app", 6)
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(
            200,
            json=[
                {"number": 5, "state": "closed", "updated_at": "2026-10-26T11:00:00Z"},
                {"number": 6, "state": "closed"},
                {"number": 7, "state": "closed", "pull_request": {}},
            ],
        )

    _serve(monkeypatch, handler)
    await integration_sync.run_due(15, maker=maker, now=NOW)

    assert calls[0].host == "api.github.com"
    assert calls[0].path == "/repos/acme/app/issues"
    assert calls[0].params["since"] == "2026-10-25T11:55:00Z"
    defect = await _get(maker, Defect, defect_id)
    assert (defect.external_issue_state, defect.status) == ("closed", "Closed")
    change = await _get(maker, ChangeRequest, change_id)
    assert (change.external_issue_state, change.status) == ("closed", "Submitted")
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert (setting.sync_updated, setting.synced_at) == (2, NOW)


@pytest.mark.asyncio
async def test_only_a_closed_issue_open_again_reopens_a_defect(maker, monkeypatch):
    project, _ = await _github(maker)
    working = await _defect(maker, project, "github", "acme/app", 5, status="In Progress")
    reopened = await _defect(
        maker,
        project,
        "github",
        "acme/app",
        6,
        status="Closed",
        external_issue_state="closed",
        external_issue_closed=True,
    )
    closed_in_bloom = await _defect(
        maker,
        project,
        "github",
        "acme/app",
        7,
        status="Closed",
        external_issue_state="open",
        external_issue_closed=False,
    )
    _serve(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json=[
                {"number": 5, "state": "open"},
                {"number": 6, "state": "open"},
                {"number": 7, "state": "open", "title": "commented"},
            ],
        ),
    )

    await integration_sync.run_due(15, maker=maker, now=NOW)

    assert (await _get(maker, Defect, working)).status == "In Progress"
    row = await _get(maker, Defect, reopened)
    assert (row.status, row.closed_at, row.external_issue_closed) == ("Open", None, False)
    assert (await _get(maker, Defect, closed_in_bloom)).status == "Closed"


@pytest.mark.asyncio
async def test_a_defect_reopened_in_bloom_stays_open_while_its_issue_stays_closed(
    maker, monkeypatch
):
    project, _ = await _github(maker)
    defect_id = await _defect(
        maker,
        project,
        "github",
        "acme/app",
        5,
        status="Open",
        external_issue_state="closed",
        external_issue_closed=True,
    )
    _serve(
        monkeypatch,
        lambda request: httpx.Response(200, json=[{"number": 5, "state": "closed"}]),
    )

    await integration_sync.run_due(15, maker=maker, now=NOW)

    assert (await _get(maker, Defect, defect_id)).status == "Open"


@pytest.mark.asyncio
async def test_a_change_request_in_its_workflow_keeps_its_status(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(maker, project, sync_full_scan=False)
    approved = await _change(maker, project, "jira", "PROJ", 99, status="Approved")
    submitted = await _change(maker, project, "jira", "PROJ", 98)
    _serve(
        monkeypatch,
        FakeJira(
            changed=[
                _issue("PROJ-99", category="done", status="Done"),
                _issue("PROJ-98", resolution={"name": "Fixed"}),
            ]
        ),
    )

    await integration_sync.run_due(15, maker=maker, now=NOW)

    setting = await _get(maker, IntegrationSetting, setting_id)
    assert (setting.sync_error, setting.synced_at) == (None, NOW)
    change = await _get(maker, ChangeRequest, approved)
    assert (change.status, change.external_issue_state) == ("Approved", "Done")
    assert (await _get(maker, ChangeRequest, submitted)).status == "Closed"


@pytest.mark.parametrize(
    "base_url,host", [("https://git.example.test/", "git.example.test"), (None, "gitlab.com")]
)
@pytest.mark.asyncio
async def test_gitlab_uses_the_base_url_or_gitlab_com(maker, monkeypatch, base_url, host):
    project, _ = await _github(maker, tracker="gitlab", base_url=base_url)
    defect_id = await _defect(maker, project, "gitlab", "grp/app", 3)
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(200, json=[{"iid": 3, "state": "closed"}])

    _serve(monkeypatch, handler)
    await integration_sync.run_due(15, maker=maker, now=NOW)

    assert calls[0].host == host
    assert calls[0].raw_path.startswith(b"/api/v4/projects/grp%2Fapp/issues")
    assert (await _get(maker, Defect, defect_id)).status == "Closed"


@pytest.mark.asyncio
async def test_an_unreadable_repository_is_skipped_and_named(maker, monkeypatch):
    project, setting_id = await _github(maker)
    defect_id = await _defect(maker, project, "github", "acme/app", 5)
    await _defect(maker, project, "github", "acme/gone", 1)
    gone = {"status": 404}

    def handler(request):
        if request.url.path.startswith("/repos/acme/gone"):
            return httpx.Response(gone["status"], json=[])
        return httpx.Response(200, json=[{"number": 5, "state": "closed"}])

    _serve(monkeypatch, handler)
    await integration_sync.run_due(15, maker=maker, now=NOW)

    assert (await _get(maker, Defect, defect_id)).status == "Closed"
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.synced_at == NOW
    assert setting.sync_warning == "GitHub answered 404 for acme/gone"
    assert setting.sync_error is None

    gone["status"] = 200
    await integration_sync.run_due(15, maker=maker, now=LATER)
    assert (await _get(maker, IntegrationSetting, setting_id)).sync_warning is None


@pytest.mark.parametrize(
    "status,headers,body",
    [
        (403, {"x-ratelimit-remaining": "0"}, {}),
        (403, {"retry-after": "60"}, {}),
        (403, {}, {"message": "You have exceeded a secondary rate limit."}),
        (429, {}, {}),
        (503, {}, {}),
    ],
)
@pytest.mark.asyncio
async def test_rate_limits_and_outages_are_run_errors(maker, monkeypatch, status, headers, body):
    project, setting_id = await _github(maker)
    await _defect(maker, project, "github", "acme/app", 5)
    _serve(monkeypatch, lambda request: httpx.Response(status, headers=headers, json=body))

    await integration_sync.run_due(15, maker=maker, now=NOW)

    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.sync_error == f"GitHub answered {status} to the issue list."
    assert (setting.synced_at, setting.sync_warning) == (None, None)


@pytest.mark.asyncio
async def test_github_redirects_are_followed_only_on_its_api_host(maker, monkeypatch):
    project, setting_id = await _github(maker)
    defect_id = await _defect(maker, project, "github", "acme/app", 5)
    location = {"url": "https://api.github.com/repositories/9/issues?page=1"}
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path.startswith("/repos/acme/app"):
            return httpx.Response(301, headers={"location": location["url"]})
        return httpx.Response(200, json=[{"number": 5, "state": "closed"}])

    _serve(monkeypatch, handler)
    await integration_sync.run_due(15, maker=maker, now=NOW)
    assert (await _get(maker, Defect, defect_id)).status == "Closed"
    assert calls[1] == location["url"]

    location["url"] = "https://elsewhere.test/issues"
    calls.clear()
    await integration_sync.run_due(15, maker=maker, now=LATER)
    assert len(calls) == 1
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.sync_error == "GitHub answered 301 to the issue list."


@pytest.mark.asyncio
async def test_gitlab_redirects_are_not_followed(maker, monkeypatch):
    project, setting_id = await _github(
        maker, tracker="gitlab", base_url="https://git.example.test"
    )
    await _defect(maker, project, "gitlab", "grp/app", 3)
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx.Response(302, headers={"location": "https://other.example.test/x"})

    _serve(monkeypatch, handler)
    await integration_sync.run_due(15, maker=maker, now=NOW)

    assert [c.host for c in calls] == ["git.example.test"]
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.sync_error == "GitLab answered 302 to the issue list."


@pytest.mark.asyncio
async def test_jira_failures_keep_the_last_success(maker, monkeypatch):
    project = await _project(maker)
    before = NOW - timedelta(hours=1)
    setting_id = await _setting(
        maker, project, synced_at=before, sync_created=3, sync_updated=4, sync_full_scan=False
    )
    _serve(monkeypatch, lambda request: httpx.Response(401))
    await integration_sync.run_due(15, maker=maker, now=NOW)
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.sync_error.startswith("Jira did not accept the account email")
    assert (setting.synced_at, setting.sync_created, setting.sync_updated) == (before, 3, 4)

    def unreachable(request):
        raise httpx.ConnectError("no route", request=request)

    _serve(monkeypatch, unreachable)
    await integration_sync.run_due(15, maker=maker, now=LATER)
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.sync_error.startswith("Jira is unreachable")
    assert (setting.synced_at, setting.sync_full_scan) == (before, False)


@pytest.mark.asyncio
async def test_a_failing_setting_does_not_stop_the_next(maker, monkeypatch):
    first = await _setting(maker, await _project(maker, "ONE"))
    second = await _setting(maker, await _project(maker, "TWO"), jira_project_key="OTHER")
    original = integration_sync._fetch_jira

    async def fetch(setting, **kw):
        if setting.jira_project_key == "PROJ":
            raise RuntimeError("boom")
        return await original(setting, **kw)

    monkeypatch.setattr(integration_sync, "_fetch_jira", fetch)
    _serve(monkeypatch, FakeJira())

    assert await integration_sync.run_due(15, maker=maker, now=NOW) == [second]
    assert (await _get(maker, IntegrationSetting, first)).sync_error == "Sync failed: boom"
    assert (await _get(maker, IntegrationSetting, second)).synced_at == NOW


@pytest.mark.asyncio
async def test_settings_not_due_disabled_or_without_credentials_are_left_alone(maker, monkeypatch):
    recent = await _setting(
        maker, await _project(maker, "REC"), sync_checked_at=NOW - timedelta(minutes=5)
    )
    disabled = await _setting(
        maker, await _project(maker, "DIS"), enabled=False, jira_project_key="DIS"
    )
    tokenless = await _setting(maker, await _project(maker, "TOK"), "github", token_encrypted=None)
    calls = []
    _serve(monkeypatch, lambda request: calls.append(request) or httpx.Response(500))

    assert await integration_sync.run_due(15, maker=maker, now=NOW) == []

    assert calls == []
    recent_row = await _get(maker, IntegrationSetting, recent)
    assert recent_row.sync_checked_at == NOW - timedelta(minutes=5)
    for setting_id in (disabled, tokenless):
        setting = await _get(maker, IntegrationSetting, setting_id)
        assert (setting.sync_checked_at, setting.sync_error) == (None, None)


@pytest.mark.asyncio
async def test_a_second_claim_within_the_interval_loses(maker):
    setting_id = await _setting(maker, await _project(maker))
    assert await integration_sync.claim(maker, setting_id, 15, NOW) is True
    assert await integration_sync.claim(maker, setting_id, 15, NOW) is False
    assert await integration_sync.claim(maker, setting_id, 15, LATER) is True


@pytest.mark.asyncio
async def test_a_run_that_changes_nothing_writes_no_event_or_update_time(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(maker, project, sync_full_scan=False)
    await _defect(maker, project, "jira", "PROJ", 42)
    updated_at = (await _get(maker, IntegrationSetting, setting_id)).updated_at
    _serve(monkeypatch, FakeJira(changed=[_issue("PROJ-42", summary="Same")]))

    await integration_sync.run_due(15, maker=maker, now=NOW)
    first = len(await _events(maker))
    await integration_sync.run_due(15, maker=maker, now=LATER)

    assert first == 1
    assert len(await _events(maker)) == 1
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert (setting.updated_at, setting.sync_updated) == (updated_at, 0)


@pytest.mark.asyncio
async def test_a_defect_appearing_during_the_search_is_not_created_twice(maker, monkeypatch):
    project = await _project(maker)
    await _setting(maker, project)
    original = integration_sync._fetch_jira

    async def fetch(setting, **kw):
        fetched = await original(setting, **kw)
        await _defect(maker, project, "jira", "PROJ", 1)
        return fetched

    monkeypatch.setattr(integration_sync, "_fetch_jira", fetch)
    _serve(monkeypatch, FakeJira(creation=[_issue("PROJ-1")]))

    await integration_sync.run_due(15, maker=maker, now=NOW)

    async with maker() as db:
        assert await db.scalar(select(func.count(Defect.id))) == 1


async def _sync_now(maker, setting_id, email):
    async with maker() as db:
        admin = User(email=email, full_name="Ada", hashed_password="x", role=UserRole.admin)
        db.add(admin)
        await db.flush()
        result = await integrations.pull_jira_issues(setting_id, db=db, current_user=admin)
        await db.commit()
        return result


@pytest.mark.asyncio
async def test_sync_now_runs_the_whole_sync(maker, monkeypatch):
    project = await _project(maker)
    setting_id = await _setting(maker, project, create_defects_on_inbound=False)
    await _defect(maker, project, "jira", "PROJ", 42)
    change_id = await _change(maker, project, "jira", "PROJ", 99)
    jira = FakeJira(
        creation=[_issue("PROJ-1")],
        changed=[_issue("PROJ-42", summary="Renamed")],
        issue_status={"PROJ-99": 500},
    )
    _serve(monkeypatch, jira)

    result = await _sync_now(maker, setting_id, "a@acme.test")

    assert (result.created, result.updated, result.removed) == (1, 1, 0)
    assert jira.reads == ["PROJ-99"]
    assert (await _get(maker, ChangeRequest, change_id)).external_issue_state is None
    async with maker() as db:
        created = (await db.scalars(select(Defect).where(Defect.external_issue_number == 1))).one()
        event = (
            await db.scalars(select(DefectSyncEvent).where(DefectSyncEvent.defect_id == created.id))
        ).one()
    assert event.event_type == "pulled"
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert setting.synced_at is not None
    assert (setting.sync_removal_cursor, setting.sync_created, setting.sync_updated) == (99, 1, 1)


@pytest.mark.asyncio
async def test_sync_now_continues_a_capped_full_search(maker, monkeypatch):
    setting_id = await _setting(maker, await _project(maker))
    monkeypatch.setattr(integrations, "MAX_PULLED_ISSUES", 1)
    monkeypatch.setattr(integration_sync, "MAX_PULLED_ISSUES", 1)
    jira = FakeJira(creation=[_issue("PROJ-1", created="2026-10-20T10:00:00.000+0000")])
    _serve(monkeypatch, jira)

    await _sync_now(maker, setting_id, "a@acme.test")
    setting = await _get(maker, IntegrationSetting, setting_id)
    assert (setting.sync_full_scan, setting.sync_scan_from) == (True, datetime(2026, 10, 20, 10))

    await _sync_now(maker, setting_id, "b@acme.test")
    creation_jql = [q for q in jira.jql if "statusCategory != Done" in q]
    assert "created >= -" in creation_jql[1]


@pytest.mark.asyncio
async def test_the_settings_response_carries_the_sync_state(maker, monkeypatch):
    setting_id = await _setting(
        maker,
        await _project(maker),
        sync_checked_at=NOW,
        synced_at=NOW,
        sync_warning="w",
        sync_created=2,
        sync_updated=5,
    )
    monkeypatch.setattr(integrations.app_settings, "INTEGRATION_SYNC_MINUTES", 7)
    response = integrations._setting_response(await _get(maker, IntegrationSetting, setting_id))
    data = json.loads(response.model_dump_json())
    assert data["synced_at"] == "2026-10-26T12:00:00Z"
    assert data["sync_checked_at"] == "2026-10-26T12:00:00Z"
    assert (data["sync_warning"], data["sync_error"]) == ("w", None)
    assert (data["sync_created"], data["sync_updated"], data["auto_sync_minutes"]) == (2, 5, 7)


@pytest.mark.parametrize("minutes,started", [(5, [5]), (0, [])])
@pytest.mark.asyncio
async def test_the_lifespan_starts_the_sync_only_when_an_interval_is_set(
    monkeypatch, minutes, started
):
    calls = []

    async def fake_loop(interval):
        calls.append(interval)
        await asyncio.Event().wait()

    class Report:
        leader_acquired = False

    async def fake_reconcile(session):
        return Report()

    monkeypatch.setattr(main.settings, "INTEGRATION_SYNC_MINUTES", minutes)
    monkeypatch.setattr(main.settings, "RUN_STARTUP_DATA_REPAIR", False)
    monkeypatch.setattr(main.settings, "AUTO_SEED_ADMIN", False)
    monkeypatch.setattr(main.integration_sync, "sync_loop", fake_loop)
    monkeypatch.setattr(main, "reconcile_attachments", fake_reconcile)

    async with main.lifespan(main.app):
        await asyncio.sleep(0)
    assert calls == started
