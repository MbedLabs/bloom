"""Scheduled sync of every project's issue tracker integration.

Each enabled integration that has what its tracker needs is synced once per interval:
Jira issues matching the project's filter become defects, linked Jira issues carry their
changes and deletions onto their defects and change requests, and linked GitHub and
GitLab issues carry their state. A run reads, calls the tracker outside any transaction,
then writes under the setting's lock and records its result on the setting.
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import httpx
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.integrations import (
    GITHUB_STATUS_MAP,
    GITLAB_STATUS_MAP,
    JIRA_ISSUE_DELETED,
    MAX_PULLED_ISSUES,
    JiraCredentialError,
    _find_jira_target,
    _follow_issue,
    _jira_api_base,
    _log_target_sync_event,
    _new_defect_from_issue,
    _split_jira_key,
    apply_issue_state,
    follow_jira_target,
    jira_headers,
    jira_search_pages,
    lock_setting,
    tracker_status,
)
from app.core.database import async_session_maker
from app.models import ChangeRequest, Defect, IntegrationSetting
from app.services.integration_secrets import decrypt_integration_secret
from app.services.jira_inbound import (
    REMOVED_STATE,
    build_jql,
    changed_jql,
    issue_matches,
    search_fields,
)

logger = logging.getLogger(__name__)

OVERLAP = timedelta(minutes=5)
REMOVAL_CHECKS = 50
PASS_SECONDS = 60
PAGE_SIZE = 100
MAX_REDIRECTS = 5
GITHUB_API = "https://api.github.com"
TRACKER_LABELS = {"jira": "Jira", "github": "GitHub", "gitlab": "GitLab"}
SKIP_STATUSES = {403, 404, 410}


class SyncError(Exception):
    """A failed run, with the text recorded on the setting."""


@dataclass
class SyncRun:
    """What one run found and changed."""

    searched: int = 0
    created: int = 0
    already_linked: int = 0
    skipped: int = 0
    updated: int = 0
    removed: int = 0
    new_ids: list[str] = field(default_factory=list)


@dataclass
class _JiraFetch:
    """The Jira answers of one run."""

    full: bool
    started: datetime
    creation: Optional[list[dict]]
    changed: list[dict]
    removed: list[int]
    checked_until: Optional[int]


@dataclass
class _ListFetch:
    """The GitHub or GitLab answers of one run."""

    lists: list[tuple[str, list[dict]]]
    skipped: list[str]
    capped_at: list[datetime]


def _now() -> datetime:
    """The current time as naive UTC, as Bloom stores times."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def has_credentials(setting: IntegrationSetting) -> bool:
    """True when the setting has what its tracker needs to be read."""
    if setting.tracker == "jira":
        return bool(
            setting.base_url
            and setting.account_email
            and setting.token_encrypted
            and setting.jira_project_key
        )
    return bool(setting.token_encrypted)


def _window_start(setting: IntegrationSetting) -> datetime:
    """Where the next run's window starts: the last success, else the setting's creation,
    with the overlap before it."""
    return (setting.synced_at or setting.created_at or _now()) - OVERLAP


def _minutes_since(start: datetime, now: datetime) -> int:
    """Whole minutes from ``start`` to ``now``, at least one."""
    return max(1, math.ceil((now - start).total_seconds() / 60))


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    """A tracker timestamp as naive UTC, or None for an unreadable value."""
    if not value:
        return None
    text = value.replace("Z", "+0000")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, fmt).astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            continue
    return None


async def _record(db: AsyncSession, setting_id: int, **values) -> None:
    """Write sync columns of a setting without moving its ``updated_at``."""
    await db.execute(
        update(IntegrationSetting)
        .where(IntegrationSetting.id == setting_id)
        .values(**values, updated_at=IntegrationSetting.updated_at)
        .execution_options(synchronize_session=False)
    )


async def claim(maker: async_sessionmaker, setting_id: int, minutes: int, now: datetime) -> bool:
    """Mark the setting as checked now when it is due; True only for the caller that did."""
    cutoff = now - timedelta(minutes=minutes)
    async with maker() as db:
        result = await db.execute(
            update(IntegrationSetting)
            .where(
                IntegrationSetting.id == setting_id,
                or_(
                    IntegrationSetting.sync_checked_at.is_(None),
                    IntegrationSetting.sync_checked_at < cutoff,
                ),
            )
            .values(sync_checked_at=now, updated_at=IntegrationSetting.updated_at)
            .execution_options(synchronize_session=False)
        )
        await db.commit()
        return result.rowcount == 1


async def _removal_candidates(db: AsyncSession, setting: IntegrationSetting) -> list[int]:
    """Issue numbers of the project's linked Jira targets not marked removed, from the
    deletion cursor on and then from the start."""
    numbers: set[int] = set()
    for model in (Defect, ChangeRequest):
        rows = await db.scalars(
            select(model.external_issue_number).where(
                model.project_id == setting.project_id,
                model.external_tracker == "jira",
                model.external_repo_full_name == setting.jira_project_key,
                model.external_issue_number.is_not(None),
                or_(
                    model.external_issue_state.is_(None),
                    model.external_issue_state != REMOVED_STATE,
                ),
            )
        )
        numbers.update(rows.all())
    ordered = sorted(numbers)
    cursor = setting.sync_removal_cursor or 0
    return [n for n in ordered if n > cursor] + [n for n in ordered if n <= cursor]


def _numbers_of(project_key: str, issues: list[dict]) -> set[int]:
    """The issue numbers of the given project among the issues."""
    found = set()
    for issue in issues:
        split = _split_jira_key(issue.get("key", "") or "")
        if split and split[0] == project_key:
            found.add(split[1])
    return found


async def _fetch_jira(
    setting: IntegrationSetting,
    *,
    create: bool,
    full: bool,
    candidates: list[int],
    now: datetime,
) -> _JiraFetch:
    """Search Jira for issues to create and issues changed in the window, and check
    linked issues for deletion."""
    headers = jira_headers(setting)
    fields = search_fields(setting) + ["created", "updated"]
    window = _minutes_since(_window_start(setting), now)
    creation = None
    async with httpx.AsyncClient(timeout=30) as client:
        base = await _jira_api_base(client, setting, headers)
        if create:
            if not full:
                jql = build_jql(setting, updated_within=window)
            elif setting.sync_scan_from:
                jql = build_jql(
                    setting,
                    created_within=_minutes_since(setting.sync_scan_from, now) + 1,
                )
            else:
                jql = build_jql(setting)
            creation = await jira_search_pages(client, base, headers, jql, fields)
        changed = await jira_search_pages(
            client, base, headers, changed_jql(setting, window), fields
        )
        seen = _numbers_of(setting.jira_project_key, (creation or []) + changed)
        removed: list[int] = []
        checked_until = None
        checks = 0
        for number in candidates:
            if number in seen:
                continue
            if checks >= REMOVAL_CHECKS:
                break
            checks += 1
            checked_until = number
            try:
                resp = await client.get(
                    f"{base}/rest/api/3/issue/{setting.jira_project_key}-{number}",
                    params={"fields": "status"},
                    headers=headers,
                )
            except httpx.RequestError:
                continue
            if resp.status_code == 404:
                removed.append(number)
    return _JiraFetch(
        full=full,
        started=now,
        creation=creation,
        changed=changed,
        removed=removed,
        checked_until=checked_until,
    )


async def _create_matching(
    db: AsyncSession,
    setting: IntegrationSetting,
    issues: list[dict],
    manual: bool,
    run: SyncRun,
) -> set[tuple[str, int]]:
    """Create the defects of the unlinked matching issues; returns their keys."""
    created: set[tuple[str, int]] = set()
    for issue in issues:
        split = _split_jira_key(issue.get("key", "") or "")
        fields = issue.get("fields", {}) or {}
        if not split or not issue_matches(setting, fields):
            run.skipped += 1
            continue
        if await _find_jira_target(db, *split) is not None:
            run.already_linked += 1
            continue
        defect = await _new_defect_from_issue(
            db, setting, *split, fields, event_type="pulled" if manual else "synced"
        )
        run.created += 1
        run.new_ids.append(defect.defect_id)
        created.add(split)
    run.searched = len(issues)
    return created


async def _follow_changed(
    db: AsyncSession,
    setting: IntegrationSetting,
    issues: list[dict],
    skip: set[tuple[str, int]],
    run: SyncRun,
) -> None:
    """Carry each changed issue onto its linked target, as a webhook update does."""
    for issue in issues:
        split = _split_jira_key(issue.get("key", "") or "")
        found = await _find_jira_target(db, *split) if split and split not in skip else None
        if found is None:
            continue
        kind, target = found
        if await follow_jira_target(
            db,
            kind,
            target,
            setting,
            "jira:issue_updated",
            issue.get("fields", {}) or {},
            f"{split[0]}-{split[1]}",
            event_type="synced",
            log_unchanged=False,
            workflow_status=False,
        ):
            run.updated += 1


async def _mark_removed(
    db: AsyncSession, setting: IntegrationSetting, numbers: list[int], run: SyncRun
) -> None:
    """Mark the linked targets of deleted issues removed, as the deletion webhook does."""
    for number in numbers:
        found = await _find_jira_target(db, setting.jira_project_key, number)
        if found is None or found[1].external_issue_state == REMOVED_STATE:
            continue
        kind, target = found
        _follow_issue(
            kind,
            target,
            setting,
            JIRA_ISSUE_DELETED,
            {},
            f"{setting.jira_project_key}-{number}",
        )
        _log_target_sync_event(
            db,
            kind,
            target.id,
            "inbound",
            "jira",
            "synced",
            payload_summary="removed in tracker",
        )
        run.removed += 1


def _last_time(issues: list[dict], name: str) -> Optional[datetime]:
    """The given time field of the last issue, as naive UTC."""
    return _parse_time((issues[-1].get("fields") or {}).get(name)) if issues else None


def _jira_values(fetched: _JiraFetch, run: SyncRun, now: datetime) -> dict:
    """The sync columns a successful Jira run records."""
    values: dict = {
        "sync_checked_at": now,
        "synced_at": now,
        "sync_error": None,
        "sync_warning": None,
        "sync_created": run.created,
        "sync_updated": run.updated + run.removed,
    }
    if len(fetched.changed) >= MAX_PULLED_ISSUES:
        values["synced_at"] = min(_last_time(fetched.changed, "updated") or now, now)
    if fetched.checked_until is not None:
        values["sync_removal_cursor"] = fetched.checked_until
    return values


def _scan_values(fetched: _JiraFetch) -> dict:
    """The full-scan columns a successful full Jira creation search records."""
    if fetched.creation is None or not fetched.full:
        return {}
    capped = len(fetched.creation) >= MAX_PULLED_ISSUES
    return {
        "sync_full_scan": capped,
        "sync_scan_from": _last_time(fetched.creation, "created") if capped else None,
    }


async def _apply_jira(
    db: AsyncSession,
    setting: IntegrationSetting,
    fetched: _JiraFetch,
    *,
    manual: bool,
    now: datetime,
) -> SyncRun:
    """Create, follow and mark removed what the Jira answers call for, under the setting's
    lock, and record the run on the setting."""
    await lock_setting(db, setting.id)
    run = SyncRun()
    created = await _create_matching(db, setting, fetched.creation or [], manual, run)
    await _follow_changed(db, setting, fetched.changed, created, run)
    await _mark_removed(db, setting, fetched.removed, run)
    await db.flush()
    await _record(db, setting.id, **_jira_values(fetched, run, now))
    scan = _scan_values(fetched)
    if scan:
        await db.execute(
            update(IntegrationSetting)
            .where(
                IntegrationSetting.id == setting.id,
                IntegrationSetting.updated_at <= fetched.started,
            )
            .values(**scan, updated_at=IntegrationSetting.updated_at)
            .execution_options(synchronize_session=False)
        )
    return run


async def sync_now(db: AsyncSession, setting: IntegrationSetting) -> SyncRun:
    """Run the whole Jira sync of one setting at once in the caller's session.

    The creation search is a full one and creates defects whatever the inbound-creation
    flag says. Jira errors are raised to the caller.
    """
    now = _now()
    candidates = await _removal_candidates(db, setting)
    fetched = await _fetch_jira(setting, create=True, full=True, candidates=candidates, now=now)
    return await _apply_jira(db, setting, fetched, manual=True, now=now)


async def _linked_repos(db: AsyncSession, setting: IntegrationSetting) -> list[str]:
    """The repositories of the project's defects and change requests linked to the tracker."""
    repos: set[str] = set()
    for model in (Defect, ChangeRequest):
        rows = await db.scalars(
            select(model.external_repo_full_name)
            .where(
                model.project_id == setting.project_id,
                model.external_tracker == setting.tracker,
                model.external_repo_full_name.is_not(None),
                model.external_issue_number.is_not(None),
            )
            .distinct()
        )
        repos.update(rows.all())
    return sorted(repos)


def _rate_limited(resp: httpx.Response) -> bool:
    """True for a rate limit: any 429, or a 403 with Retry-After, X-RateLimit-Remaining 0
    or a rate limit message."""
    if resp.status_code == 429:
        return True
    if resp.status_code != 403:
        return False
    if "retry-after" in resp.headers or resp.headers.get("x-ratelimit-remaining") == "0":
        return True
    try:
        body = resp.json()
    except ValueError:
        return False
    return isinstance(body, dict) and "rate limit" in str(body.get("message", "")).lower()


async def _get(
    client: httpx.AsyncClient, tracker: str, url: str, params: dict, headers: dict
) -> httpx.Response:
    """GET a list page; GitHub redirects are followed while they stay on its API host."""
    resp = await client.get(url, params=params, headers=headers)
    hops = 0
    while resp.is_redirect and tracker == "github" and hops < MAX_REDIRECTS:
        target = resp.url.join(resp.headers.get("location", ""))
        if target.scheme != "https" or target.host != httpx.URL(GITHUB_API).host:
            break
        resp = await client.get(target, headers=headers)
        hops += 1
    return resp


def _list_request(setting: IntegrationSetting, repo: str, since: str) -> tuple[str, dict, dict]:
    """URL, query and headers of the issue list of one repository."""
    token = decrypt_integration_secret(setting.token_encrypted)
    if setting.tracker == "github":
        return (
            f"{GITHUB_API}/repos/{repo}/issues",
            {"state": "all", "since": since, "sort": "updated", "direction": "asc"},
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
    base = (setting.base_url or "https://gitlab.com").rstrip("/")
    return (
        f"{base}/api/v4/projects/{quote(repo, safe='')}/issues",
        {"updated_after": since, "order_by": "updated_at", "sort": "asc"},
        {"PRIVATE-TOKEN": token},
    )


async def _list_repo(
    client: httpx.AsyncClient, setting: IntegrationSetting, repo: str, since: str
) -> tuple[Optional[list[dict]], Optional[int]]:
    """The issues of one repository updated since the window start, or no issues and the
    status the tracker answered when the repository is gone or unreadable. Raises
    SyncError for any other failure."""
    label = TRACKER_LABELS[setting.tracker]
    url, query, headers = _list_request(setting, repo, since)
    items: list[dict] = []
    page = 1
    while len(items) < MAX_PULLED_ISSUES:
        try:
            resp = await _get(
                client,
                setting.tracker,
                url,
                {**query, "per_page": PAGE_SIZE, "page": page},
                headers,
            )
        except httpx.RequestError as exc:
            raise SyncError(f"{label} is unreachable: {exc}") from exc
        if not resp.is_success:
            if resp.status_code in SKIP_STATUSES and not _rate_limited(resp):
                return None, resp.status_code
            raise SyncError(f"{label} answered {resp.status_code} to the issue list.")
        batch = resp.json()
        if not isinstance(batch, list):
            raise SyncError(f"{label} answered {resp.status_code} to the issue list.")
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        page += 1
    return items[:MAX_PULLED_ISSUES], None


async def _fetch_lists(setting: IntegrationSetting, repos: list[str]) -> _ListFetch:
    """The issue lists of every linked repository, with the repositories skipped."""
    label = TRACKER_LABELS[setting.tracker]
    since = _window_start(setting).strftime("%Y-%m-%dT%H:%M:%SZ")
    fetched = _ListFetch(lists=[], skipped=[], capped_at=[])
    async with httpx.AsyncClient(timeout=30) as client:
        for repo in repos:
            items, refused = await _list_repo(client, setting, repo, since)
            if items is None:
                fetched.skipped.append(f"{label} answered {refused} for {repo}")
                continue
            fetched.lists.append((repo, items))
            if len(items) >= MAX_PULLED_ISSUES:
                last = _parse_time(items[-1].get("updated_at"))
                if last:
                    fetched.capped_at.append(last)
    return fetched


def _apply_state(db: AsyncSession, model, target, status_map: dict, state: str) -> bool:
    """Set one target's issue state, and a defect's status, when they differ; log it."""
    old_state = target.external_issue_state
    if model is Defect:
        closed = status_map.get(state) == "Closed"
        wanted = tracker_status(target.status, closed, target.external_issue_closed is True)
        unchanged_status = wanted is None or target.status == wanted
        if old_state == state and unchanged_status and target.external_issue_closed == closed:
            return False
        apply_issue_state(target, status_map, state)
        kind = "defect"
    else:
        if old_state == state:
            return False
        target.external_issue_state = state
        target.external_last_event_at = _now()
        kind = "change_request"
    _log_target_sync_event(
        db,
        kind,
        target.id,
        "inbound",
        target.external_tracker,
        "synced",
        payload_summary=f"state: {old_state} -> {state}",
    )
    return True


async def _linked_targets(db: AsyncSession, setting: IntegrationSetting, repo: str, number):
    """The project's defects and change requests linked to one issue of a repository."""
    found = []
    for model in (Defect, ChangeRequest):
        rows = await db.scalars(
            select(model).where(
                model.project_id == setting.project_id,
                model.external_tracker == setting.tracker,
                model.external_repo_full_name == repo,
                model.external_issue_number == number,
            )
        )
        found.extend((model, row) for row in rows.all())
    return found


async def _apply_lists(
    db: AsyncSession, setting: IntegrationSetting, fetched: _ListFetch, now: datetime
) -> SyncRun:
    """Carry each listed issue's state onto its linked defects and change requests, under
    the setting's lock, and record the run on the setting."""
    await lock_setting(db, setting.id)
    run = SyncRun()
    status_map = GITHUB_STATUS_MAP if setting.tracker == "github" else GITLAB_STATUS_MAP
    number_key = "number" if setting.tracker == "github" else "iid"
    for repo, items in fetched.lists:
        for item in items:
            number, state = item.get(number_key), item.get("state")
            if not number or not state or "pull_request" in item:
                continue
            for model, target in await _linked_targets(db, setting, repo, number):
                run.updated += _apply_state(db, model, target, status_map, state)
    await db.flush()
    await _record(
        db,
        setting.id,
        sync_checked_at=now,
        synced_at=min([now, *fetched.capped_at]),
        sync_error=None,
        sync_warning="; ".join(fetched.skipped) or None,
        sync_created=0,
        sync_updated=run.updated,
    )
    return run


def _jira_error(exc: Exception) -> str:
    """The recorded text of a Jira failure."""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"Jira answered {exc.response.status_code} to the search."
    if isinstance(exc, httpx.RequestError):
        return f"Jira is unreachable: {exc}"
    return str(exc)


async def sync_setting(maker: async_sessionmaker, setting_id: int, now: datetime) -> SyncRun:
    """One scheduled run of a claimed setting: read, call the tracker, then write.

    Raises SyncError with the text to record when the tracker fails.
    """
    async with maker() as db:
        setting = await db.get(IntegrationSetting, setting_id)
        if setting.tracker == "jira":
            candidates = await _removal_candidates(db, setting)
        else:
            repos = await _linked_repos(db, setting)
        await db.commit()

    if setting.tracker == "jira":
        try:
            fetched = await _fetch_jira(
                setting,
                create=bool(setting.create_defects_on_inbound),
                full=bool(setting.sync_full_scan),
                candidates=candidates,
                now=now,
            )
        except (JiraCredentialError, httpx.HTTPError) as exc:
            raise SyncError(_jira_error(exc)) from exc
    else:
        lists = await _fetch_lists(setting, repos)

    async with maker() as db:
        setting = await db.get(IntegrationSetting, setting_id)
        if setting.tracker == "jira":
            run = await _apply_jira(db, setting, fetched, manual=False, now=now)
        else:
            run = await _apply_lists(db, setting, lists, now)
        await db.commit()
    return run


async def _record_error(maker: async_sessionmaker, setting_id: int, text: str) -> None:
    """Record a failed run on the setting, keeping its last success and counts."""
    async with maker() as db:
        await _record(db, setting_id, sync_error=text[:2000])
        await db.commit()


async def run_due(
    minutes: int,
    *,
    maker: async_sessionmaker = async_session_maker,
    now: Optional[datetime] = None,
) -> list[int]:
    """Sync every due setting this process claims; returns the ids it synced."""
    now = now or _now()
    cutoff = now - timedelta(minutes=minutes)
    async with maker() as db:
        rows = await db.scalars(
            select(IntegrationSetting)
            .where(
                IntegrationSetting.enabled.is_(True),
                or_(
                    IntegrationSetting.sync_checked_at.is_(None),
                    IntegrationSetting.sync_checked_at < cutoff,
                ),
            )
            .order_by(IntegrationSetting.id)
        )
        due = [row.id for row in rows.all() if has_credentials(row)]
    synced = []
    for setting_id in due:
        if not await claim(maker, setting_id, minutes, now):
            continue
        try:
            await sync_setting(maker, setting_id, now)
            synced.append(setting_id)
        except SyncError as exc:
            await _record_error(maker, setting_id, str(exc))
        except Exception as exc:
            logger.exception("Integration sync of setting %s failed", setting_id)
            await _record_error(maker, setting_id, f"Sync failed: {exc}")
    return synced


async def sync_loop(minutes: int) -> None:
    """Run a sync pass every minute, the first one minute after start, for as long as the
    application runs."""
    while True:
        await asyncio.sleep(PASS_SECONDS)
        try:
            await run_due(minutes)
        except Exception:
            logger.exception("Integration sync pass failed")
