"""Bloom to Jira: the Jira issue a defect creates, and who is told when Jira refuses it.

A defect created since the installation's ``defects_to_jira_since`` marker and linked to no
tracker is sent while the direction of the project's Jira integration includes Bloom to
Jira, and is then linked to the issue Jira creates. A sync takes a defect before creating
its issue by setting its ``jira_send_started_at`` in a committed transaction of its own, and
only one sync can take it. The claim is cleared when the defect is linked or Jira has
certainly not created the issue. A claim older than ``CLAIM_TIMEOUT`` has no known outcome:
the next sync searches Jira for the issue and links it, or takes the defect over and sends
it again. A defect Jira refuses, or that fails to reach Jira, stays saved; its first failure
is emailed to the recipients ``failure_recipients`` collects. A defect Jira refused with a
4xx answer is sent again by Sync now, and by the automatic sync only once the defect has
changed since that refusal.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.integrations import (
    JIRA_TO_BLOOM,
    JiraCredentialError,
    _find_jira_target,
    _jira_api_base,
    _log_target_sync_event,
    _split_jira_key,
    jira_headers,
    jira_search_pages,
)
from app.api.workflow import document_path
from app.core.config import settings
from app.models import (
    Defect,
    DefectSyncEvent,
    Group,
    IntegrationSetting,
    Project,
    ProjectAccess,
    SystemMarker,
    TestCase,
)
from app.models.user import User, UserRole
from app.services.jira_inbound import _quote, issue_url
from app.services.mail_service import (
    MailConfigurationError,
    send_jira_create_failed_email,
)

logger = logging.getLogger(__name__)

ISSUE_TYPE = "Bug"
SUMMARY_LIMIT = 255
PRODUCT_OWNERS_GROUP = "Product Owners"
CREATED_EVENT = "issue_created"
CREATE_FAILED_EVENT = "issue_create_failed"
CREATE_REFUSED_EVENT = "issue_create_refused"
SENDS_SINCE = "defects_to_jira_since"
CLAIM_TIMEOUT = timedelta(minutes=10)
SEARCH_MARGIN = timedelta(days=1)
CLOCK_MARGIN = timedelta(minutes=5)
_RICH_TEXT_SYSTEM_FIELDS = {"description", "environment"}


@dataclass
class SendRun:
    """The defect ids one send linked to a new Jira issue and the ones Jira did not take."""

    sent: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


@dataclass
class Outgoing:
    """A defect to send: its database id, the fields of its Jira Bug, its test case id and,
    for a defect whose earlier send has no known outcome, the time of that send's claim."""

    defect_pk: int
    fields: dict
    tc_id: Optional[str]
    claimed_at: Optional[datetime] = None


@dataclass
class Answer:
    """Jira's answer to one send: the project key and number of the issue, whether it was
    found by search or created, or why there is none, whether Jira has certainly
    not created it and whether Jira refused it with a 4xx answer; with the claim this send
    holds, if any."""

    defect_pk: int
    issue: Optional[tuple[str, int]] = None
    found: bool = False
    error: Optional[str] = None
    not_created: bool = False
    refused: bool = False
    claimed_at: Optional[datetime] = None


def text_to_adf(text: str) -> Optional[dict]:
    """An Atlassian Document Format document with one paragraph per non-empty line of
    the text, or None when the text has none."""
    lines = [line.strip() for line in (text or "").splitlines()]
    paragraphs = [
        {"type": "paragraph", "content": [{"type": "text", "text": line}]} for line in lines if line
    ]
    if not paragraphs:
        return None
    return {"type": "doc", "version": 1, "content": paragraphs}


def issue_fields(setting: IntegrationSetting, defect: Defect) -> dict:
    """The fields of the Jira Bug a defect creates, but its test case reference: its
    title as summary, its description and the configured label."""
    fields: dict = {
        "project": {"key": setting.jira_project_key},
        "issuetype": {"name": ISSUE_TYPE},
        "summary": " ".join((defect.title or defect.defect_id).split())[:SUMMARY_LIMIT],
    }
    description = text_to_adf(defect.description or "")
    if description:
        fields["description"] = description
    if setting.jira_label:
        fields["labels"] = [setting.jira_label]
    return fields


async def failure_recipients(db: AsyncSession, project_id: int) -> list[User]:
    """The active users told of a defect Jira did not take: the administrators and the
    project's Product Owners."""
    admins = await db.scalars(
        select(User).where(User.role == UserRole.admin, User.is_active.is_(True))
    )
    owners = await db.scalars(
        select(User)
        .join(ProjectAccess, ProjectAccess.user_id == User.id)
        .join(Group, Group.id == ProjectAccess.policy_group_id)
        .where(
            ProjectAccess.project_id == project_id,
            Group.name == PRODUCT_OWNERS_GROUP,
            User.is_active.is_(True),
        )
    )
    found: dict[int, User] = {}
    for user in [*admins.all(), *owners.all()]:
        found.setdefault(user.id, user)
    return list(found.values())


async def _test_case_id(db: AsyncSession, defect: Defect) -> Optional[str]:
    """The id of the test case the defect comes from, if any."""
    if defect.source_type != "TC" or defect.source_id is None:
        return None
    return await db.scalar(
        select(TestCase.tc_id).where(
            TestCase.id == defect.source_id, TestCase.project_id == defect.project_id
        )
    )


async def _reference_is_rich(
    client: httpx.AsyncClient, base: str, headers: dict, field_id: str
) -> bool:
    """True when Jira takes the reference field as an Atlassian document."""
    resp = await client.get(f"{base}/rest/api/3/field", headers=headers)
    resp.raise_for_status()
    for item in resp.json() or []:
        if item.get("id") != field_id:
            continue
        schema = item.get("schema") or {}
        return (schema.get("custom") or "").endswith(":textarea") or (
            schema.get("system") in _RICH_TEXT_SYSTEM_FIELDS
        )
    return False


def _refusal(exc: Exception) -> str:
    """A readable reason for a failed create."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            body = exc.response.json() or {}
        except ValueError:
            body = {}
        details = list(body.get("errorMessages") or [])
        details += [f"{name}: {text}" for name, text in (body.get("errors") or {}).items()]
        reason = "; ".join(details) or exc.response.reason_phrase
        return f"Jira answered {exc.response.status_code}: {reason}"[:2000]
    if isinstance(exc, httpx.RequestError):
        return f"Jira is unreachable: {exc}"[:2000]
    return str(exc)[:2000]


def _not_created(exc: Exception) -> bool:
    """True when a failed create request certainly created no issue: Jira refused it with
    a client error, or the request never reached Jira."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code < 500
    return isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout))


def _refused(exc: Exception) -> bool:
    """True when Jira answered a failed create with a 4xx status."""
    return isinstance(exc, httpx.HTTPStatusError) and 400 <= exc.response.status_code < 500


async def _create_issue(
    client: httpx.AsyncClient, base: str, headers: dict, fields: dict
) -> tuple[str, int]:
    """Create the Jira issue and return its project key and number."""
    resp = await client.post(f"{base}/rest/api/3/issue", json={"fields": fields}, headers=headers)
    resp.raise_for_status()
    split = _split_jira_key((resp.json() or {}).get("key", "") or "")
    if not split:
        raise ValueError("Jira did not answer with the key of the new issue.")
    return split


def _link(setting: IntegrationSetting, defect: Defect, project_key: str, number: int) -> None:
    """Link the defect to the Jira issue created for it."""
    defect.external_tracker = "jira"
    defect.external_repo_full_name = project_key
    defect.external_issue_number = number
    defect.external_issue_url = issue_url(setting, f"{project_key}-{number}")
    defect.external_issue_closed = False
    defect.external_last_event_at = datetime.now(timezone.utc).replace(tzinfo=None)


async def _failed_before(db: AsyncSession, defect_id: int) -> bool:
    """True when an earlier send of the defect failed or was refused."""
    return (
        await db.scalar(
            select(DefectSyncEvent.id)
            .where(
                DefectSyncEvent.defect_id == defect_id,
                DefectSyncEvent.direction == "outbound",
                DefectSyncEvent.event_type.in_((CREATE_FAILED_EVENT, CREATE_REFUSED_EVENT)),
            )
            .limit(1)
        )
    ) is not None


async def _refused_since_change(db: AsyncSession, defect: Defect) -> bool:
    """True when the defect's last outbound sync event is a refusal by Jira recorded no
    earlier than the defect's last change."""
    event = await db.scalar(
        select(DefectSyncEvent)
        .where(
            DefectSyncEvent.defect_id == defect.id,
            DefectSyncEvent.direction == "outbound",
        )
        .order_by(DefectSyncEvent.id.desc())
        .limit(1)
    )
    return (
        event is not None
        and event.event_type == CREATE_REFUSED_EVENT
        and defect.updated_at <= event.created_at
    )


async def _tell_failure(db: AsyncSession, defect: Defect, error: str) -> None:
    """Email the failure of a defect to each recipient."""
    project = await db.get(Project, defect.project_id)
    link = f"{settings.APP_BASE_URL.rstrip('/')}{await document_path(db, defect)}"
    for user in await failure_recipients(db, defect.project_id):
        try:
            send_jira_create_failed_email(
                to_email=user.email,
                recipient_name=user.full_name,
                defect_id=defect.defect_id,
                defect_title=defect.title,
                project=project.prefix if project else "",
                error=error,
                defect_link=link,
            )
        except MailConfigurationError:
            logger.warning("Jira create failure of defect %s was not emailed", defect.id)


async def _fail(db: AsyncSession, defect: Defect, error: str, refused: bool, run: SendRun) -> None:
    """Record a failed send, as a refusal when Jira refused it with a 4xx answer, and tell
    its first failure."""
    first = not await _failed_before(db, defect.id)
    _log_target_sync_event(
        db,
        "defect",
        defect.id,
        "outbound",
        "jira",
        CREATE_REFUSED_EVENT if refused else CREATE_FAILED_EVENT,
        success=False,
        error=error,
    )
    run.failed.append(defect.defect_id)
    if first:
        await _tell_failure(db, defect, error)


async def defects_to_send(
    db: AsyncSession, setting: IntegrationSetting, now: datetime, *, manual: bool = False
) -> list[Defect]:
    """The defects of the setting's project created since the ``SENDS_SINCE`` marker and
    linked to no tracker, either taken by no sync or taken more than ``CLAIM_TIMEOUT``
    ago, oldest first; none when the marker is missing. Unless ``manual``, a defect taken
    by no sync whose last send Jira refused and that has not changed since is left out."""
    since = await db.scalar(select(SystemMarker.marked_at).where(SystemMarker.name == SENDS_SINCE))
    if since is None:
        return []
    rows = await db.scalars(
        select(Defect)
        .where(
            Defect.project_id == setting.project_id,
            Defect.external_tracker.is_(None),
            or_(
                Defect.jira_send_started_at.is_(None),
                Defect.jira_send_started_at < now - CLAIM_TIMEOUT,
            ),
            Defect.created_at >= since,
        )
        .order_by(Defect.created_at, Defect.id)
    )
    return [
        defect
        for defect in rows.all()
        if manual
        or defect.jira_send_started_at is not None
        or not await _refused_since_change(db, defect)
    ]


async def prepare_sends(
    db: AsyncSession, setting: IntegrationSetting, *, manual: bool = False
) -> list[Outgoing]:
    """The defects ``defects_to_send`` returns with the fields of their Jira Bug and the
    claim of an earlier send without a known outcome, while the setting is a Jira
    integration whose direction includes Bloom to Jira."""
    if setting.tracker != "jira" or setting.direction == JIRA_TO_BLOOM:
        return []
    return [
        Outgoing(
            defect.id,
            issue_fields(setting, defect),
            await _test_case_id(db, defect),
            defect.jira_send_started_at,
        )
        for defect in await defects_to_send(db, setting, _now(), manual=manual)
    ]


def _now() -> datetime:
    """The current time as naive UTC, as Bloom stores times."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _take(
    maker: async_sessionmaker, defect_pk: int, previous: Optional[datetime]
) -> Optional[datetime]:
    """Take the defect for one send in a transaction committed before Jira is called: an
    unlinked defect taken by no sync, or still held by the claim ``previous``. Returns the
    new claim, or None when another sync holds it or it is linked."""
    claim = _now()
    held = (
        Defect.jira_send_started_at.is_(None)
        if previous is None
        else Defect.jira_send_started_at == previous
    )
    async with maker() as db:
        result = await db.execute(
            update(Defect)
            .where(Defect.id == defect_pk, Defect.external_tracker.is_(None), held)
            .values(jira_send_started_at=claim, updated_at=Defect.updated_at)
            .execution_options(synchronize_session=False)
        )
        await db.commit()
    return claim if result.rowcount == 1 else None


async def _give_back(db: AsyncSession, defect_pk: int, claim: Optional[datetime]) -> None:
    """Clear the defect's send claim; with ``claim``, only while it is still that claim."""
    query = update(Defect).where(Defect.id == defect_pk)
    if claim is not None:
        query = query.where(Defect.jira_send_started_at == claim)
    await db.execute(
        query.values(jira_send_started_at=None, updated_at=Defect.updated_at).execution_options(
            synchronize_session=False
        )
    )


async def _find_sent_issue(
    client: httpx.AsyncClient,
    base: str,
    headers: dict,
    setting: IntegrationSetting,
    item: Outgoing,
    taken: set[tuple[str, int]],
) -> Optional[tuple[str, int]]:
    """The first issue of the Jira project with the defect's summary and the configured
    label, created no earlier than ``CLOCK_MARGIN`` before the earlier send's claim, that no
    other send of this run found."""
    from app.services.integration_sync import _parse_time

    claimed_at = item.claimed_at
    clauses = [
        f"project = {_quote(setting.jira_project_key)}",
        f'created >= "{(claimed_at - SEARCH_MARGIN):%Y/%m/%d %H:%M}"',
    ]
    if setting.jira_label:
        clauses.append(f"labels = {_quote(setting.jira_label)}")
    jql = " AND ".join(clauses) + " ORDER BY created ASC"
    issues = await jira_search_pages(client, base, headers, jql, ["summary", "labels", "created"])
    for issue in issues:
        fields = issue.get("fields") or {}
        split = _split_jira_key(issue.get("key", "") or "")
        created = _parse_time(fields.get("created"))
        if (
            split
            and split not in taken
            and fields.get("summary") == item.fields["summary"]
            and created is not None
            and created >= claimed_at - CLOCK_MARGIN
            and (not setting.jira_label or setting.jira_label in (fields.get("labels") or []))
        ):
            return split
    return None


async def _post(
    client: httpx.AsyncClient,
    base: str,
    headers: dict,
    item: Outgoing,
    fields: dict,
    claim: datetime,
) -> Answer:
    """Create the Jira issue of a taken defect and return Jira's answer."""
    try:
        issue = await _create_issue(client, base, headers, fields)
    except (httpx.HTTPError, ValueError) as exc:
        return Answer(
            item.defect_pk,
            error=_refusal(exc),
            not_created=_not_created(exc),
            refused=_refused(exc),
            claimed_at=claim,
        )
    return Answer(item.defect_pk, issue=issue, claimed_at=claim)


async def send_to_jira(
    maker: async_sessionmaker, setting: IntegrationSetting, outgoing: list[Outgoing]
) -> list[Answer]:
    """Send each prepared defect: a defect whose earlier send has no known outcome is
    first searched for in Jira and, when no issue is found, taken over and sent again;
    every other defect is taken and its Jira Bug created, with its test case id in the
    configured reference field. Returns Jira's answer for each defect this run handled."""
    if not outgoing:
        return []
    try:
        headers = jira_headers(setting)
    except ValueError as exc:
        return [
            Answer(item.defect_pk, error=_refusal(exc), not_created=True)
            for item in outgoing
            if item.claimed_at is None
        ]
    reference = setting.jira_reference_field
    answers: list[Answer] = []
    found: set[tuple[str, int]] = set()
    async with httpx.AsyncClient(timeout=15) as client:
        base: Optional[str] = None
        rich_reference: Optional[bool] = None
        for item in outgoing:
            try:
                if base is None:
                    base = await _jira_api_base(client, setting, headers)
                if item.claimed_at is not None:
                    issue = await _find_sent_issue(client, base, headers, setting, item, found)
                    if issue is not None:
                        found.add(issue)
                        answers.append(
                            Answer(
                                item.defect_pk,
                                issue=issue,
                                found=True,
                                claimed_at=item.claimed_at,
                            )
                        )
                        continue
                fields = dict(item.fields)
                if reference and item.tc_id:
                    if rich_reference is None:
                        rich_reference = await _reference_is_rich(client, base, headers, reference)
                    fields[reference] = text_to_adf(item.tc_id) if rich_reference else item.tc_id
            except (JiraCredentialError, httpx.HTTPError, ValueError) as exc:
                if item.claimed_at is None:
                    answers.append(Answer(item.defect_pk, error=_refusal(exc), not_created=True))
                continue
            claim = await _take(maker, item.defect_pk, item.claimed_at)
            if claim is None:
                continue
            answers.append(await _post(client, base, headers, item, fields, claim))
    return answers


async def record_sends(
    db: AsyncSession, setting: IntegrationSetting, answers: list[Answer]
) -> SendRun:
    """Link each defect still unlinked to the issue created or found for it and clear its
    claim; a found issue linked to another defect gives the claim back. Record a
    failure or refusal and tell the first one, giving the claim back only when Jira has
    certainly not created the issue."""
    run = SendRun()
    for answer in answers:
        defect = await db.get(Defect, answer.defect_pk)
        if defect is None:
            continue
        await db.refresh(defect)
        if defect.external_tracker:
            continue
        if answer.issue is None:
            if answer.not_created and answer.claimed_at is not None:
                await _give_back(db, defect.id, answer.claimed_at)
            await _fail(db, defect, answer.error or "", answer.refused, run)
            continue
        project_key, number = answer.issue
        if answer.found and await _find_jira_target(db, project_key, number) is not None:
            await _give_back(db, defect.id, answer.claimed_at)
            continue
        await _give_back(db, defect.id, None)
        _link(setting, defect, project_key, number)
        _log_target_sync_event(
            db,
            "defect",
            defect.id,
            "outbound",
            "jira",
            CREATED_EVENT,
            payload_summary=(
                f"found {project_key}-{number}"
                if answer.found
                else f"created {project_key}-{number}"
            ),
        )
        run.sent.append(defect.defect_id)
    await db.flush()
    return run
