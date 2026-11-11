"""
* @file     ${tests/parameters.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Constants of Bloom's tests: drawn test data, expected values and messages.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Test data is drawn from SEED; BUDTEST_SEED repeats a run with the same data.
"""

import hashlib
import os
import random
import string
from datetime import datetime, timedelta, timezone

SEED = int(os.environ.get("BUDTEST_SEED") or random.SystemRandom().randrange(1, 10**9))
_draw = random.Random(SEED)


def _letters(alphabet: str, low: int, high: int) -> str:
    """A drawn word of ``low`` to ``high`` letters from ``alphabet``."""
    return "".join(_draw.choices(alphabet, k=_draw.randint(low, high)))


_WORDS = ["valve", "sensor", "drift", "reset", "timeout", "relay", "fault", "bus", "boot", "flash"]

SYNC_DATABASE = "sqlite+aiosqlite:///:memory:"
SYNC_PROJECT_PREFIX = _letters(string.ascii_uppercase, 3, 3)
SYNC_OTHER_PREFIX = _letters(string.ascii_uppercase, 4, 4)
SYNC_TOKEN = _letters(string.ascii_letters + string.digits, 24, 32)
JIRA_URL = f"https://{_letters(string.ascii_lowercase, 6, 10)}.atlassian.net"
JIRA_ACCOUNT = f"{_letters(string.ascii_lowercase, 4, 8)}@example.com"
JIRA_PROJECT = _letters(string.ascii_uppercase, 2, 6)
JIRA_OTHER_PROJECT = JIRA_PROJECT + "X"
JIRA_MYSELF = "/rest/api/3/myself"
JIRA_SEARCH = "/rest/api/3/search/jql"
JIRA_ISSUE = "/rest/api/3/issue/"
GITHUB_API = "api.github.com"
GITLAB_COM = "gitlab.com"
GITLAB_HOST = f"git.{_letters(string.ascii_lowercase, 5, 8)}.example"
_owner = _letters(string.ascii_lowercase, 3, 8)
_repos = _draw.sample(["app", "fw", "gui", "cloud", "tools"], 2)
REPO = f"{_owner}/{_repos[0]}"
OTHER_REPO = f"{_owner}/{_repos[1]}"
ADMIN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
OTHER_ADMIN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"

LINKED_NUMBER, NEW_NUMBER, TASK_NUMBER, CHANGE_NUMBER = _draw.sample(range(1, 10_000), 4)
REMOVED_NUMBERS = tuple(sorted(_draw.sample(range(1, 10_000), 2)))
GIT_NUMBERS = _draw.sample(range(1, 5_000), 4)
NEW_SUMMARY = " ".join(_draw.sample(_WORDS, 4))
OLD_TITLE = " ".join(_draw.sample(_WORDS, 3))
CHANGED_TITLE = " ".join(_draw.sample(_WORDS, 5))
CHANGED_DESCRIPTION = " ".join(_draw.sample(_WORDS, 6))
SAME_SUMMARY = " ".join(_draw.sample(_WORDS, 2))
LABEL = _draw.choice(_WORDS)
FAILURE_TEXT = _draw.choice(_WORDS)
JIRA_PRIORITY_MAP = {
    "Highest": "Critical",
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
    "Lowest": "Low",
}
JIRA_PRIORITY = _draw.choice(sorted(JIRA_PRIORITY_MAP))
BLOOM_PRIORITY = JIRA_PRIORITY_MAP[JIRA_PRIORITY]
NOW = datetime(2025, 1, 1) + timedelta(minutes=_draw.randrange(0, 365 * 24 * 60))
SETTING_AGE = timedelta(minutes=_draw.randrange(11, 60 * 24 * 30))
LAST_SYNC_MINUTES = _draw.randrange(11, 600)
LAST_SYNC = timedelta(minutes=LAST_SYNC_MINUTES)
LATER = timedelta(minutes=_draw.randrange(11, 120))
RECENT_CHECK = timedelta(minutes=_draw.randrange(1, 10))
SAVE_OFFSET = timedelta(seconds=_draw.randrange(1, 60))
OVERLAP_MINUTES = 5
FIRST_CREATED = NOW - timedelta(minutes=_draw.randrange(6 * 24 * 60, 300 * 24 * 60))
SECOND_CREATED = FIRST_CREATED + timedelta(minutes=_draw.randrange(1, 5 * 24 * 60))
CREATED_OFFSET = _draw.randrange(-11, 13)
UPDATED_OFFSET = _draw.randrange(-11, 13)
RETRY_AFTER = str(_draw.randrange(1, 3600))
OUTAGE_STATUS = _draw.choice([500, 502, 503, 504])
MOVED = _draw.choice([301, 302, 307, 308])
REDIRECTED = f"https://api.github.com/repositories/{_draw.randrange(1, 10**6)}/issues?page=1"
FOREIGN = f"https://{_letters(string.ascii_lowercase, 6, 10)}.test/issues"
SYNC_RATE = _draw.randrange(5, 60)
PREVIOUS_COUNTS = (_draw.randrange(1, 50), _draw.randrange(1, 50))
WARNING_TEXT = " ".join(_draw.sample(_WORDS, 3))

STATUS_OK = 200
STATUS_FORBIDDEN = 403
STATUS_NOT_FOUND = 404
STATUS_UNAUTHORIZED = 401
STATUS_TOO_MANY = 429
STATUS_SERVER_ERROR = 500
BUG = "Bug"
TASK = "Task"
JIRA_NEW = "new"
JIRA_DONE_CATEGORY = "done"
JIRA_TO_DO = "To Do"
JIRA_DONE = "Done"
JIRA_FIXED = "Fixed"
DEFECT_OPEN = "Open"
DEFECT_CLOSED = "Closed"
DEFECT_IN_PROGRESS = "In Progress"
CHANGE_SUBMITTED = "Submitted"
CHANGE_APPROVED = "Approved"
GIT_OPEN = "open"
GIT_CLOSED = "closed"
REMOVED_STATE = "Removed in Jira"
SYNCED_EVENT = "synced"
PULLED_EVENT = "pulled"
REMOVED_EVENT = "removed in tracker"
CREATED_FROM = "created from {key}"
CREATION_MARK = "statusCategory != Done"
CREATION_JQL = (
    'project = "{project}" AND issuetype in ("Bug") AND statusCategory != Done ORDER BY created ASC'
)
WINDOW_CREATION_JQL = (
    'project = "{project}" AND issuetype in ("Bug") AND statusCategory != Done '
    "AND updated >= -{minutes}m ORDER BY created ASC"
)
WINDOW_CHANGED_JQL = 'project = "{project}" AND updated >= -{minutes}m ORDER BY updated ASC'
CREATED_WINDOW = "created >= -"
UPDATED_WINDOW = "updated >="
API_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CLAIM_MINUTES = 10
SEARCH_CAP = 2
SYNC_NOW_CAP = 1
REMOVAL_CHECKS = 1
GITHUB_WARNING = "GitHub answered 404 for {repo}"
LIST_ERROR = "{tracker} answered {status} to the issue list."
JIRA_REFUSED_ACCOUNT = "Jira did not accept the account email"
JIRA_UNREACHABLE = "Jira is unreachable"
SYNC_FAILED = "Sync failed: {text}"
SECONDARY_RATE_LIMIT = "You have exceeded a secondary rate limit."
OUTAGES = [
    (STATUS_FORBIDDEN, {"x-ratelimit-remaining": "0"}, {}),
    (STATUS_FORBIDDEN, {"retry-after": RETRY_AFTER}, {}),
    (STATUS_FORBIDDEN, {}, {"message": SECONDARY_RATE_LIMIT}),
    (STATUS_TOO_MANY, {}, {}),
    (OUTAGE_STATUS, {}, {}),
]
OUTAGE_CASES = [(index,) for index in range(5)]
GITLAB_HOSTS = [(f"https://{GITLAB_HOST}/", GITLAB_HOST), (None, GITLAB_COM)]
LIFESPAN_SWITCHES = [(SYNC_RATE, 1), (None, 1), (0, 0)]
LIFESPAN_CASES = [(index,) for index in range(len(LIFESPAN_SWITCHES))]

MSG_SETTING_SYNCED = "the due setting is synced"
MSG_CREATION_SEARCH_OPEN_BUGS = "the creation search asks for the project's open Bugs"
MSG_NEW_BUG_ONE_DEFECT = "the new Bug becomes one defect"
MSG_NO_TASK_NO_DUPLICATE = "the linked issue is not created again and the Task is skipped"
MSG_NEW_DEFECT_CONTENT = (
    "the new defect has the Jira summary as title, the setting's project and status Open"
)
MSG_FULL_SCAN_CLEARED = "the full scan is cleared"
MSG_RUN_STAMPED = "the run is recorded as checked and successful at NOW"
MSG_RUN_COUNTS = "the run created 1, updated 0, with no error"
MSG_ORIGIN_LOGGED = "the new defect logs the issue it came from"
MSG_NO_CREATION_SEARCH = "with creation off no creation search runs"
MSG_ONLY_LINKED = "only the linked defect exists"
MSG_LINKED_CLOSED = "the linked defect is Closed"
MSG_NOT_CREATED_TWICE = "a defect linked during the search is not created a second time"
MSG_CAPPED_KEEPS_FULL_SCAN = "a capped run keeps the full scan"
MSG_CAPPED_CONTINUES_FROM = "a capped run continues from the last created issue, in UTC"
MSG_CAPPED_SYNCED_UP_TO = "a capped run is synced up to the last update it saw, in UTC"
MSG_NEXT_SEARCH_BY_CREATION = "the next creation search goes by creation time"
MSG_NEXT_SEARCH_NOT_BY_UPDATE = "the next creation search ignores update time"
MSG_WINDOW = "both searches cover the time since the last sync plus the 5-minute overlap"
MSG_DEFECT_FOLLOWS = (
    "the defect takes the Jira status, title, mapped priority, description and state"
)
MSG_CHANGE_CLOSED = "the change request is Closed"
MSG_TWO_UPDATES = "the run counts 2 updates"
MSG_ONE_SYNC_EVENT = "the record logs one sync"
MSG_WORKFLOW_RUN_OK = "the run succeeds at NOW"
MSG_APPROVED_KEPT = "a change request in its workflow keeps Approved and takes the issue state"
MSG_SUBMITTED_CLOSED = "a submitted change request whose issue is resolved is Closed"
MSG_UNCHANGED_FIRST_EVENT = "the first run logs the follow-up"
MSG_UNCHANGED_NO_EVENT = "a run that changes nothing logs no event"
MSG_UNCHANGED_SETTING = (
    "a run that changes nothing leaves the setting's update time and count alone"
)
MSG_FIRST_READ = "the first run reads the lowest linked issue"
MSG_GONE_REMOVED = "the gone issue's defect is marked removed"
MSG_CURSOR_FIRST = "the cursor stops at it and one update is counted"
MSG_REMOVAL_LOGGED = "the defect logs its removal"
MSG_SECOND_READ = "the second run reads the next linked issue"
MSG_FORBIDDEN_UNMARKED = (
    "a forbidden issue leaves the change request unmarked and the cursor moves on without an error"
)
MSG_REFUSED_ACCOUNT = "a refused account is the run's error"
MSG_LAST_SUCCESS_KEPT = "a failed run keeps the last success and its counts"
MSG_UNREACHABLE = "an unreachable Jira is the run's error"
MSG_UNREACHABLE_KEEPS = "an unreachable Jira keeps the last success and the scan state"
MSG_OTHER_SETTING_SYNCED = "only the setting that did not fail is synced"
MSG_FAILURE_RECORDED = "the failing setting records its error"
MSG_OTHER_STAMPED = "the other setting is synced at NOW"
MSG_GITHUB_CALL = (
    "the repository's issue list on GitHub's API, since the setting's creation minus the overlap"
)
MSG_GIT_DEFECT_CLOSED = "the defect of a closed issue is Closed"
MSG_GIT_CHANGE_STATE_ONLY = "the change request takes the state and keeps its status"
MSG_GIT_COUNTS = "2 updates, synced at NOW; the pull request is ignored"
MSG_WORKING_KEPT = "an open issue leaves a working defect In Progress"
MSG_REOPENED = "an issue open again reopens its defect"
MSG_CLOSED_IN_BLOOM_KEPT = "a defect closed in Bloom while its issue stayed open stays Closed"
MSG_REOPENED_IN_BLOOM_KEPT = "a defect reopened in Bloom stays Open while its issue stays closed"
MSG_GITLAB_HOST = "GitLab is called on the configured base URL, else on gitlab.com"
MSG_GITLAB_PATH = "the issue list of the encoded repository path"
MSG_READABLE_SYNCED = "the readable repository's defect is Closed"
MSG_UNREADABLE_WARNING = "the run succeeds at NOW with a warning naming the unreadable repository"
MSG_WARNING_CLEARED = "the warning clears once the repository reads again"
MSG_OUTAGE_ERROR = "a rate limit or an outage is the run's error, with no success and no warning"
MSG_REDIRECT_FOLLOWED = "a redirect inside GitHub's API is followed"
MSG_FOREIGN_NOT_FOLLOWED = "a redirect to another host is not followed"
MSG_REDIRECT_ERROR = "the run's error names the redirect"
MSG_GITLAB_ONLY_HOST = "only the configured GitLab host is called"
MSG_NOTHING_SYNCED = "a pass with no due, enabled and credentialed setting syncs nothing"
MSG_NOTHING_CALLED = "no tracker is called"
MSG_NOT_DUE_UNTOUCHED = "a setting checked recently keeps its check time"
MSG_SKIPPED_UNTOUCHED = "a disabled or tokenless setting records nothing"
MSG_FIRST_CLAIM = "the first claim wins"
MSG_SECOND_CLAIM = "a second claim within the rate loses"
MSG_LATER_CLAIM = "a claim after the rate wins"
MSG_SAVE_RESCAN = "saving the setting asks for a full scan from the start"
MSG_SAVE_DURING_SCAN = "a save during a full scan keeps the rescan, and the run still succeeds"
MSG_LIFESPAN = "the application starts the sync loop unless the sync is switched off"
MSG_RESPONSE_TIMES = "the setting's sync times are given in UTC"
MSG_RESPONSE_STATE = "the setting's warning, error, counts and its own rate are given"
MSG_SYNC_NOW_COUNTS = "Sync now creates, updates and removes in one call"
MSG_SYNC_NOW_READ = "Sync now checks the linked issue"
MSG_SYNC_NOW_ERROR_UNMARKED = "a server error leaves the change request unmarked"
MSG_SYNC_NOW_EVENT = "a defect created by Sync now logs it was pulled"
MSG_SYNC_NOW_SETTING = "the setting records the run, the cursor and the counts"
MSG_SYNC_NOW_CAPPED = "a capped Sync now keeps the full scan from the last created issue"

WEBHOOK_SECRET = _letters(string.ascii_letters + string.digits, 24, 32)
WEBHOOK_SUMMARY = " ".join(_draw.sample(_WORDS, 3))
SIGNATURE_PREFIX = "sha256="
FORGED_SIGNATURE = SIGNATURE_PREFIX + "".join(_draw.choices("0123456789abcdef", k=64))
UNLINKED_NUMBER, WEBHOOK_NEW_NUMBER, WEBHOOK_REPLAY_NUMBER, WEBHOOK_OFF_NUMBER = _draw.sample(
    range(10_000, 20_000), 4
)
DELIVERIES = [_letters(string.ascii_lowercase + string.digits, 8, 12) for _ in range(12)]
CHANGE_WORKFLOW_STATUSES = ["Draft", "Review", "Approved"]
CHANGE_WORKFLOW_CASES = [(index,) for index in range(len(CHANGE_WORKFLOW_STATUSES))]
DEFECT_VERIFIED = "Verified"
JIRA_IN_REVIEW = "In Review"
JIRA_IN_PROGRESS_CATEGORY = "indeterminate"
MALFORMED_KEY = _letters(string.ascii_uppercase, 6, 9)
TC_TITLE = _draw.choice(_WORDS)
DESCRIPTION_TEXT = " ".join(_draw.sample(_WORDS, 4))
BOT_EMAIL = (
    f"{_letters(string.ascii_uppercase, 1, 1)}{_letters(string.ascii_lowercase, 4, 7)}@example.com"
)
CLOUD_ID = _letters(string.ascii_lowercase + string.digits, 8, 12)
NEXT_PAGE_TOKEN = _letters(string.ascii_letters, 6, 10)
PROBE_DEFECT_EVENT = "probe_" + _draw.choice(_WORDS)
PROBE_CHANGE_EVENT = "probe_" + _draw.choice(_WORDS) + "_change"

API_BASE = "http://bloom.test"
INTEGRATIONS_PREFIX = "/api/integrations"
WEBHOOK_PATH = "/api/integrations/jira/webhook"
ATLASSIAN_GATEWAY = "https://api.atlassian.com/ex/jira"
TENANT_INFO = "/_edge/tenant_info"
ISSUE_UPDATED = "jira:issue_updated"
ISSUE_CREATED = "jira:issue_created"
ISSUE_DELETED = "jira:issue_deleted"
WORKLOG_UPDATED = "jira:worklog_updated"
STATUS_BAD_REQUEST = 400
STATUS_CONFLICT = 409
STATUS_BAD_GATEWAY = 502
ANSWER_DUPLICATE = "duplicate"
ANSWER_IGNORED = "ignored"
ANSWER_PROCESSED = "processed"
ANSWER_CREATED = "created"
TARGET_DEFECT = "defect"
TARGET_CHANGE = "change_request"
NOT_TAKEN_IN = {"status": "ignored", "reason": "issue not taken in by this project"}
CRITICAL = "Critical"
SOURCE_TC = "TC"
UNKNOWN_SETTING_ID = 999_999
UNKNOWN_LEVEL = "Urgent"

MSG_MISSING_SIGNATURE = "a delivery without a signature is refused with 403"
MSG_WRONG_SIGNATURE = "a delivery with a wrong signature is refused with 403"
MSG_FOREIGN_SIGNATURE = "a signature lifted from another delivery is refused with 403"
MSG_MISSING_DELIVERY = "a delivery without an identifier is refused with 400"
MSG_DEFECT_TARGET = "a signed update of a linked issue answers 200 for the defect"
MSG_DEFECT_CLOSED_BY_WEBHOOK = "the linked defect is Closed"
MSG_CHANGE_TARGET = "a signed update of a linked issue answers 200 for the change request"
MSG_CHANGE_CLOSED_BY_WEBHOOK = "the linked change request is Closed"
MSG_REPEAT_IS_DUPLICATE = "the same delivery again answers duplicate"
MSG_ONE_SUCCESS_EVENT = "the change request logs one successful sync"
MSG_WORKFLOW_CONFLICT = (
    "a closure that would skip the change workflow is refused with 409 and the status stays"
)
MSG_FORGED_LEGACY = "a forged delivery cannot close the change request"
MSG_OTHER_STATUS_KEEPS = "a Jira status other than done leaves the Bloom status"
MSG_DONE_CLOSES = "a done Jira status closes the defect"
MSG_REOPEN_OPENS = "a Jira status out of done reopens a defect Jira closed"
MSG_BLOOM_CLOSE_KEPT = "a defect closed in Bloom stays Closed"
MSG_REPLAY_DUPLICATE = "a replayed delivery answers duplicate"
MSG_REPLAY_NO_CHANGE = "a replayed delivery changes nothing"
MSG_UNLINKED_404 = "an issue linked to nothing is not found"
MSG_NON_ISSUE_IGNORED = "an event that is not about an issue is ignored"
MSG_MALFORMED_IGNORED = "a malformed issue key is ignored"
MSG_NO_SPOOFED_EVENTS = "a refused delivery logs no successful sync on either log"
MSG_EVENTS_ROUTED = "defect and change request events land in their own logs"
MSG_INBOUND_CREATED = "an unmatched issue of a mapped project creates a defect"
MSG_INBOUND_CONTENT = "the created defect takes the Jira summary and is Open"
MSG_INBOUND_IDEMPOTENT = "a replayed create delivery makes no second defect"
MSG_INBOUND_OFF = "with creation off an unmatched issue is not found"
MSG_COPIES_ISSUE = "the created defect copies the description, priority, severity, URL, test case, state and reporter"
MSG_TASK_IGNORED = "a Task is ignored"
MSG_UNLABELLED_IGNORED = "an issue without the configured label is ignored"
MSG_LABELLED_CREATED = "an issue with the configured label creates a defect without a reporter"
MSG_UNKNOWN_DELETE_IGNORED = "a deletion of an issue Bloom never had is ignored"
MSG_FOLLOWS_ISSUE = (
    "the linked defect takes the Jira title, description and priority and stays Open"
)
MSG_RESOLUTION_CLOSES = "a Jira resolution closes the defect with a closing time"
MSG_DELETED_KEPT = "a deleted issue marks its defect removed and keeps it"
MSG_DELETED_CHANGE = "a deleted issue marks its change request removed"
MSG_NO_PUSH_JIRA_TO_BLOOM = "edits are not pushed while the direction is Jira to Bloom"
MSG_PUSH_BOTH = "edits are pushed when the direction includes Bloom to Jira"
MSG_PULL_COUNTS = "the pull searched 4, created 1, found 1 linked and skipped 2"
MSG_PULL_NEW_ID = "the pull names the new defect"
MSG_PULL_SEARCHES = "the pull asks for open Bugs and follows the next page"
MSG_PULL_EVENT = "a pulled defect logs it was pulled"
MSG_PULL_NEEDS_KEY = "a pull without a Jira project key is refused with 400"
MSG_PULL_UNKNOWN = "a pull of an unknown integration is not found"
MSG_PULL_REFUSED = "a refused account is a 400 naming it"
MSG_PULL_UNREACHABLE = "an unreachable Jira is a 502 naming it"
MSG_FILTER_VALID = "a filter of issue types and Bloom levels is accepted"
MSG_FILTER_BLANK_TYPE = "a blank issue type is refused"
MSG_FILTER_UNKNOWN_LEVEL = "a priority map to an unknown level is refused and names it"
MSG_GATEWAY_CREATED = "a scoped token pulls through Atlassian's gateway"
MSG_GATEWAY_SEARCHES = "both searches go to the gateway of the site's cloud"
MSG_GATEWAY_URL = "the pulled defect links to the issue on the site"
MSG_RACE_PROCESSED = "a delivery whose issue was linked while it waited is processed"
MSG_RACE_NOT_DOUBLED = "the defect linked while it waited is followed, not doubled"

FILTER_NUMBERS = _draw.sample(range(20_000, 30_000), 4)
PULL_NEW_NUMBER, PULL_TASK_NUMBER, GATEWAY_NUMBER, RACE_NUMBER = _draw.sample(
    range(30_000, 40_000), 4
)
TC_NUMBER = _draw.randrange(1, 1000)
BOT_EMAIL = JIRA_ACCOUNT[0].upper() + JIRA_ACCOUNT[1:]
JIRA_HIGHEST = "Highest"
SEARCH_PATH = "/rest/api/3/search/jql"
PULL_COUNTS = (4, 1, 1, 2)
PULL_UNCHANGED = (0, 0)
DIRECTION_BOTH = "both"
THIRD_ADMIN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
FOURTH_ADMIN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"

DATABASE_SETTING = "DATABASE_URL"
POSTGRES_SCHEME = "postgresql"
PG_ADMIN_DATABASE = "postgres"
PG_DATABASE_PREFIX = "infra137_"
RACE_HOLD_SECONDS = 10
RACE_TIMEOUT_SECONDS = 20
RACE_ISSUE_NUMBER = _draw.randrange(40_000, 50_000)
MSG_NEEDS_POSTGRES = "this test needs PostgreSQL in DATABASE_URL"
MSG_BOTH_SEARCHED = "Sync now and the scheduled run both searched before either wrote"
MSG_RACE_ONE_DEFECT = "Sync now and a scheduled run at once create one defect for the issue"

CLI_PREFIX = "/api/auth/cli"
CLI_START = "/start"
CLI_APPROVE = "/approve"
CLI_DENY = "/deny"
CLI_EXCHANGE = "/exchange"
CLI_REFRESH = "/refresh"
CLI_SESSIONS = "/sessions/"
CLI_CODE_MODE = "code"
CLI_CALLBACK_MODE = "callback"
CLI_VERIFIER = _letters(string.ascii_letters + string.digits + "._~-", 43, 128)
CLI_STATE = _letters(string.ascii_letters + string.digits, 8, 32)
CLI_CLIENT_NAME = f"Client {_letters(string.ascii_lowercase, 4, 10)}"
CLI_CALLBACK_URI = f"http://127.0.0.1:{_draw.randrange(1024, 65536)}/callback"
CLI_APPROVED_CODE = _letters(string.ascii_letters + string.digits, 16, 32)
CLI_RACE_COPIES = _draw.randint(3, 6)
CLI_DENY_APPROVE_ORDER = _draw.sample([CLI_DENY, CLI_APPROVE, CLI_DENY, CLI_APPROVE], 4)
CLI_ADMIN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
CLI_REVOCATION_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
CLI_REFRESH_TOKEN = _letters(string.ascii_letters + string.digits, 24, 48)
CLI_INVALID_TOKEN = "invalid_token"
CLI_LOCK_WAIT_SECONDS = 5
CLI_LOCK_TIMEOUT = "1s"
CLI_SESSION_INDEXES = {"cli_auth_sessions_pkey", "ix_cli_auth_sessions_expires_at"}
CLI_SESSION_CASCADE = "CASCADE"
CLI_ADDED_SESSIONS = 2

MIGRATION_BEFORE_CLI = "d6f9b2c3a0e5"
MIGRATION_HEAD = "head"
RETAINED_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
RETAINED_NAME = _letters(string.ascii_uppercase, 1, 1) + _letters(string.ascii_lowercase, 4, 8)
RETAINED_PROJECT = f"Project {_letters(string.ascii_lowercase, 4, 10)}"
RETAINED_PREFIX = _letters(string.ascii_uppercase, 3, 3)
RETAINED_SESSION_VERSION = _draw.randint(2, 50)
RETAINED_TOKEN_HASH = _letters(string.hexdigits.lower(), 64, 64)

MSG_ALEMBIC_SUCCEEDS = "every Alembic command succeeds"
MSG_OLD_HEAD = "the database starts at the revision before the CLI sessions"
MSG_OLD_NO_TABLE = "the revision before the CLI sessions has no CLI session table"
MSG_UPGRADE_KEEPS_ROWS = "the upgrade keeps the account, project, refresh token and audit event"
MSG_SINGLE_HEAD = "the migrations have one head"
MSG_AT_HEAD = "the database reaches the single head"
MSG_TABLE_COLUMNS = "the CLI session table has the model's columns and nullability"
MSG_TABLE_INDEXES = "the CLI session table has its primary key and expiry index"
MSG_TABLE_CASCADE = "deleting an account deletes its CLI sessions"
MSG_TABLE_CHECK = "the mode check constraint exists"
MSG_TABLE_EMPTY = "the new CLI session table is empty"
MSG_SESSIONS_STORED = "a pending and an approved CLI session are stored"
MSG_DOWNGRADE_REVISION = "the downgrade returns to the revision before the CLI sessions"
MSG_DOWNGRADE_DROPS = "the downgrade drops the CLI session table with its sessions"
MSG_DOWNGRADE_KEEPS_ROWS = "the downgrade keeps the account, project, refresh token and audit event"
MSG_REUPGRADE_SAME = "upgrading again gives the same empty table, rows and revision"
MSG_CLI_STARTED = "the manual-code request starts"
MSG_APPROVED_ONCE = "concurrent approvals of one request succeed once"
MSG_APPROVE_LOSERS = "the other approvals are refused with 400"
MSG_EXCHANGED_ONCE = "concurrent exchanges of one code succeed once"
MSG_EXCHANGE_LOSERS = "the other exchanges are refused with 400"
MSG_REFRESHED_ONCE = "concurrent refreshes of one token succeed once"
MSG_REFRESH_LOSERS = "the other refreshes are refused with 401"
MSG_ENDED_ONCE = "concurrent denials and approvals end the request once"
MSG_END_LOSERS = "the other denials and approvals are refused with 400"
MSG_ENDED_NOT_PENDING = "an ended request is no longer found"
MSG_DENIED_EMPTY = "a denied manual-code request answers with an empty body"
MSG_DENIED_NO_EXCHANGE = "a denied request cannot be exchanged"
MSG_APPROVED_EXCHANGES = "the approved request exchanges its code"
MSG_REFRESH_WAITED = "the refresh asked for the account lock while the revocation held it"
MSG_REFRESH_REVOKED = "a refresh that waited on a revocation is refused as an invalid token"
MSG_FRESH_UPGRADE = "a fresh database upgrades to the head"
CLI_DENIED_CODE = _letters(string.ascii_letters + string.digits, 16, 32)
CLI_CONSENT_ANSWERS = (STATUS_OK, STATUS_BAD_REQUEST)
CLI_REFRESH_ANSWERS = (STATUS_OK, STATUS_UNAUTHORIZED)

PUBLIC_ID_BEFORE = "0ef8b87db4d3"
PUBLIC_ID_REVISION = "b2d4f6a8c0e1"
PUBLIC_ID_INDEXES = ["uq_test_campaigns_campaign_id", "uq_test_suites_suite_id"]
PUBLIC_ID_DUPLICATE_MESSAGE = "{column} holds duplicate public IDs"
SUITE_COLUMN = "test_suites.suite_id"
CAMPAIGN_COLUMN = "test_campaigns.campaign_id"
UNIQUE_VIOLATION = "23505"
NOT_NULL_VIOLATION = "23502"
NULLABLE = "YES"
NOT_NULLABLE = "NO"

CAMPAIGN_PREFIXES = []
while len(CAMPAIGN_PREFIXES) < 3:
    _prefix = _letters(string.ascii_uppercase, 3, 3)
    if _prefix not in CAMPAIGN_PREFIXES:
        CAMPAIGN_PREFIXES.append(_prefix)
TAKEN_PREFIX, EMPTY_PREFIX, WIDENED_PREFIX = CAMPAIGN_PREFIXES
TAKEN_NUMBER = _draw.randint(1, 50)
LOW_NUMBER = _draw.randint(1, 998)
LAST_THREE_DIGIT_NUMBER = 999


def _campaign_id(prefix: str, number: int, width: int = 3) -> str:
    """The public ID of campaign ``number`` of a project, zero-padded to ``width`` digits."""
    return f"{prefix}-CMP-{number:0{width}d}"


CAMPAIGN_SEEDS = {
    TAKEN_PREFIX: [None, _campaign_id(TAKEN_PREFIX, TAKEN_NUMBER), "", None],
    EMPTY_PREFIX: [None],
    WIDENED_PREFIX: [
        _campaign_id(WIDENED_PREFIX, LOW_NUMBER),
        _campaign_id(WIDENED_PREFIX, LAST_THREE_DIGIT_NUMBER),
        None,
    ],
}
CAMPAIGN_EXPECTED = {
    TAKEN_PREFIX: [
        _campaign_id(TAKEN_PREFIX, TAKEN_NUMBER + 1),
        _campaign_id(TAKEN_PREFIX, TAKEN_NUMBER),
        _campaign_id(TAKEN_PREFIX, TAKEN_NUMBER + 2),
        _campaign_id(TAKEN_PREFIX, TAKEN_NUMBER + 3),
    ],
    EMPTY_PREFIX: [_campaign_id(EMPTY_PREFIX, 1)],
    WIDENED_PREFIX: [
        _campaign_id(WIDENED_PREFIX, LOW_NUMBER, 4),
        _campaign_id(WIDENED_PREFIX, LAST_THREE_DIGIT_NUMBER, 4),
        _campaign_id(WIDENED_PREFIX, LAST_THREE_DIGIT_NUMBER + 1, 4),
    ],
}
DUPLICATE_SUITE_ID = f"{TAKEN_PREFIX}-TS-{_draw.randint(1, 999):03d}"
DUPLICATE_CAMPAIGN_ID = _campaign_id(TAKEN_PREFIX, _draw.randint(1, 999))
PUBLIC_ID_DUPLICATES = [
    ([DUPLICATE_SUITE_ID, DUPLICATE_SUITE_ID], [None, None], SUITE_COLUMN),
    ([None, None], [DUPLICATE_CAMPAIGN_ID, DUPLICATE_CAMPAIGN_ID], CAMPAIGN_COLUMN),
]
PUBLIC_ID_DUPLICATE_CASES = [(index,) for index in range(len(PUBLIC_ID_DUPLICATES))]

MSG_PUBLIC_IDS_NUMBERED = "campaigns without a public ID get the next free number of their project"
MSG_PUBLIC_IDS_REQUIRED = "the campaign public ID becomes required and both public IDs unique"
MSG_PUBLIC_ID_VIOLATIONS = "a repeated suite or campaign public ID and a missing one are refused"
MSG_PUBLIC_ID_DOWNGRADE = "the downgrade drops the indexes, makes the ID optional and keeps it"
MSG_PUBLIC_ID_REUPGRADE = "upgrading again restores both unique indexes"
MSG_DUPLICATES_REFUSED = "the upgrade stops on duplicate public IDs"
MSG_DUPLICATES_NAMED = "the refusal names the column holding the duplicates"
MSG_DUPLICATES_REVISION = "a refused upgrade stays at the revision before"

NEXT_ID_TYPE, NEXT_ID_OTHER_TYPE = _draw.sample(["REQ", "TC", "DES", "RSK", "CHG", "CPT", "DEF"], 2)
NEXT_ID_PREFIX, NEXT_ID_OTHER_PREFIX = CAMPAIGN_PREFIXES[:2]
NEXT_ID_UNSUPPORTED_TYPE = _letters(string.ascii_uppercase, 5, 8)
NEXT_ID_TAKEN = _draw.randint(1, 50)
NEXT_ID_LOW, NEXT_ID_HIGH = sorted(_draw.sample(range(1, 900), 2))
NEXT_ID_ROUTE = "/projects/{project_ref}/next-doc-id/{type_code}"
NEXT_ID_ERROR = "ValueError"


def _doc_id(prefix: str, type_code: str, number: int) -> str:
    """A document id in the application's format, zero-padded to three digits."""
    return f"{prefix}-{type_code}-{number:03d}"


MSG_NEXT_ID_EMPTY = "an empty project's preview is its first id"
MSG_NEXT_ID_TAKEN = "the preview advances past the id already taken"
MSG_NEXT_ID_HIGHEST = "the preview follows the highest number, so deleted ids are not reused"
MSG_NEXT_ID_OTHERS = "ids of other types and other projects are ignored"
MSG_NEXT_ID_UNSUPPORTED = "an unsupported type code is refused"
MSG_NEXT_ID_ROUTE = "the next id has its own route beside the document routes"
NEXT_ID_TAKEN_IDS = [_doc_id(NEXT_ID_PREFIX, NEXT_ID_TYPE, NEXT_ID_TAKEN)]
NEXT_ID_GAP_IDS = [
    _doc_id(NEXT_ID_PREFIX, NEXT_ID_TYPE, NEXT_ID_LOW),
    _doc_id(NEXT_ID_PREFIX, NEXT_ID_TYPE, NEXT_ID_HIGH),
]
NEXT_ID_MIXED_IDS = [
    _doc_id(NEXT_ID_PREFIX, NEXT_ID_OTHER_TYPE, NEXT_ID_HIGH),
    _doc_id(NEXT_ID_OTHER_PREFIX, NEXT_ID_TYPE, NEXT_ID_HIGH),
    _doc_id(NEXT_ID_PREFIX, NEXT_ID_TYPE, NEXT_ID_LOW),
]
NEXT_ID_FIRST = _doc_id(NEXT_ID_PREFIX, NEXT_ID_TYPE, 1)
NEXT_ID_AFTER_TAKEN = _doc_id(NEXT_ID_PREFIX, NEXT_ID_TYPE, NEXT_ID_TAKEN + 1)
NEXT_ID_AFTER_HIGH = _doc_id(NEXT_ID_PREFIX, NEXT_ID_TYPE, NEXT_ID_HIGH + 1)
NEXT_ID_AFTER_LOW = _doc_id(NEXT_ID_PREFIX, NEXT_ID_TYPE, NEXT_ID_LOW + 1)

TOKEN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
TOKEN_STANDARD = "HS256"
TOKEN_VALID_MINUTES = _draw.randint(1, 60)
TOKEN_REFUSALS = [
    (TOKEN_STANDARD, -_draw.randint(1, 60)),
    ("HS512", TOKEN_VALID_MINUTES),
    ("none", TOKEN_VALID_MINUTES),
]
TOKEN_REFUSAL_CASES = [(index,) for index in range(len(TOKEN_REFUSALS))]
MSG_TOKEN_STANDARD = "a standard HS256 token signs its user in"
MSG_TOKEN_ISSUED = "a token Bloom issues signs its user in"
MSG_TOKEN_REFUSED = "an expired token or one signed with another algorithm is refused with 401"

SMOKE_SCRIPT = "scripts/e2e_image_smoke.sh"
SMOKE_IMAGE = f"ghcr.io/mbedlabs/bloom:{_letters(string.ascii_lowercase + string.digits, 6, 12)}"
SMOKE_APP_CONTAINER = "bloom-e2e-app-"
SMOKE_ADMIN_NAME_ARGUMENT = "ADMIN_FULL_NAME=E2E Admin"
SMOKE_STOP_CODE = _draw.randint(2, 120)
SMOKE_ALEMBIC_HEAD = _letters(string.hexdigits.lower(), 12, 12)
SMOKE_PAYLOAD_PATTERN = r"-d '(\{\"name\":\"Demo\",\"prefix\":\"[^\"]+\"\})'"
MSG_SMOKE_ADMIN_NAME = "the admin full name reaches docker as one environment argument"
MSG_SMOKE_PAYLOAD_FOUND = "the script creates its project with a JSON payload"
MSG_SMOKE_PAYLOAD_VALID = "the project payload passes the current create contract"

API_ADMIN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
API_PASSWORD = _letters(string.ascii_letters + string.digits, 16, 24)
API_MEMBER_ROLE = "maintainer"
STATUS_CREATED = 201
BASELINE_PREFIXES = []
while len(BASELINE_PREFIXES) < 4:
    _prefix = _letters(string.ascii_uppercase, 3, 3)
    if _prefix not in BASELINE_PREFIXES + CAMPAIGN_PREFIXES:
        BASELINE_PREFIXES.append(_prefix)
SCOPED_PREFIX, SEPARATE_PREFIX, ADMISSION_PREFIX, OWNED_PREFIX = BASELINE_PREFIXES
BASELINE_NAME = f"Baseline {_letters(string.ascii_lowercase, 4, 10)}"
BASELINE_PERMISSIONS = {"baseline": ["view"]}
REQUIREMENT_PERMISSIONS = {"REQ": ["view"]}
REQUIREMENT_TYPES = ["REQ"]
BOTH_READS_ALLOWED = [STATUS_OK, STATUS_OK]
BOTH_READS_DENIED = [STATUS_FORBIDDEN, STATUS_FORBIDDEN]
MSG_API_SETUP = "every setup call through the API succeeds"
MSG_GROUP_ADMITTED_READS = (
    "a baseline-read group admitted to the project allows the list and the detail"
)
MSG_OVERRIDE_DENIES = "a project override without baseline read denies the list and the detail"
MSG_OVERRIDE_ALLOWS = (
    "adding baseline read to the override allows the list and the detail of the baseline"
)
MSG_OTHER_PROJECT_DENIED = "the other project's baselines stay denied"
MSG_GROUP_POLICY_KEPT = "the group keeps its own policy after the override changes"
MSG_GROUP_NEEDS_ADMISSION = "a baseline-read group without project admission denies both reads"
MSG_OWNER_AUTHORITY = "the admin and the project owner read the baseline list and detail"
BASELINE_MEMBER_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
BASELINE_POLICY_NAME = f"Policy {_letters(string.ascii_lowercase, 4, 10)}"
REQUIREMENT_POLICY_NAME = BASELINE_POLICY_NAME + " requirements"
BASELINE_GROUP_NAME = f"Group {_letters(string.ascii_lowercase, 4, 10)}"

LABELS_PREFIX = _letters(string.ascii_uppercase, 3, 3)
LABELS_REQUIREMENT_TITLE = f"Requirement {_letters(string.ascii_lowercase, 4, 10)}"
REQUIREMENT_DRAFT = "Draft"
HIDDEN_EMAIL = f"hidden-{_letters(string.ascii_lowercase, 4, 8)}@example.com"
READER_EMAIL = f"reader-{_letters(string.ascii_lowercase, 4, 8)}@example.com"
MEMBER_FULL_NAME = f"Member {_letters(string.ascii_lowercase, 4, 8)}"
TEST_CASE_PERMISSIONS = {"TC": ["view"]}
MISSING_DOC_NUMBER = _draw.randint(10**8, 10**9 - 1)
MISSING_REQUIREMENT_NUMBER = MISSING_DOC_NUMBER - _draw.randint(1, 1000)
ACCESS_REQUIREMENT = "requirement"
ACCESS_PROJECT = "project"
ACCESS_DOCUMENT = "document"
ADMIN_REQUEST_DETAIL = "Administrators hold every access, so there is nothing to request."
ALREADY_HAVE_ACCESS = "You already have access to {target}."
DELETED_LABEL = "{ref} (deleted)"
AUDIT_REQUEST_ACTION = "api.request"
AUDIT_REQUIREMENT_LABEL = "requirement {ref}"
AUDIT_USER_LABEL = "user {name}"
MSG_ID_OPENS_DOCUMENT = "a database id in a document address opens the same document as its doc id"
MSG_UNKNOWN_ID_NOT_FOUND = "an unknown id in a document address is not found"
MSG_HIDDEN_NOT_FOUND = "a member who may not read requirements gets not found"
MSG_READER_OPENS = "a member who may read requirements opens the document"
MSG_ADMIN_CANNOT_REQUEST = "an administrator's access request is refused and sends no mail"
MSG_HOLDER_CANNOT_REQUEST = "a member who holds the access cannot request it, and no mail is sent"
MSG_REQUEST_LABELS = (
    "requests show the id to the requester and the doc id or a deleted mark to admins"
)
MSG_REQUEST_MAIL = "the request mail goes to others than the requester and names the doc id"
MSG_AUDIT_LABELS = "the audit log names targets and actors, and marks a deleted target"
AUDIT_USER_TARGET = "user"

VISIBILITY_PREFIX = _letters(string.ascii_uppercase, 3, 3)
EXTERNAL_EMAIL = f"external-{_letters(string.ascii_lowercase, 4, 8)}@example.com"
EXTERNAL_ROLE = "external"
EXTERNAL_PERMISSIONS = {"*": ["view", "comment"]}
CUSTOMER_VISIBILITY = "customer"
INTERNAL_VISIBILITY = "internal"
DOCUMENT_TYPE = "SPEC"
DOCUMENT_STATUS = "Draft"
DOCUMENT_VERSION = "1.0"
CUSTOMER_DOC_NUMBER, INTERNAL_DOC_NUMBER = _draw.sample(range(1, 999), 2)
CUSTOMER_DOC_ID = _doc_id(VISIBILITY_PREFIX, DOCUMENT_TYPE, CUSTOMER_DOC_NUMBER)
INTERNAL_DOC_ID = _doc_id(VISIBILITY_PREFIX, DOCUMENT_TYPE, INTERNAL_DOC_NUMBER)
CUSTOMER_DOC_TITLE = f"Customer {_letters(string.ascii_lowercase, 4, 10)}"
INTERNAL_DOC_TITLE = f"Internal {_letters(string.ascii_lowercase, 4, 10)}"
MSG_EXTERNAL_SIGNS_IN = "the external member signs in"
MSG_EXTERNAL_LIST = (
    "an external member's document list holds the customer document and not the internal one"
)
MSG_EXTERNAL_DETAIL = "an external member opening an internal document gets not found"

ACTIVITY_PREFIX = _letters(string.ascii_uppercase, 3, 3)
ARTEFACT_PATHS = {
    "requirement": "/api/requirements",
    "test-case": "/api/test-cases",
    "design": "/api/designs",
    "change": "/api/changes",
}
DOCUMENT_KIND = "document"
REQUIREMENT_KIND = "requirement"
TEST_CASE_KIND = "test-case"
DESIGN_KIND = "design"
CHANGE_KIND = "change"
REQ_TYPE = "Safety"
REQ_ORIGIN = "Regulatory"
DOCS_TYPE_FILTER = "REQ"
ARTEFACT_TITLE = f"Artefact {_letters(string.ascii_lowercase, 4, 10)}"
RENAMED_TITLE = ARTEFACT_TITLE + " renamed"
REVIEW_COMMENT = f"Reviewed {_letters(string.ascii_lowercase, 4, 10)}"
FORGED_REVIEWED_AT = (NOW - LATER).strftime("%Y-%m-%dT%H:%M:%SZ")
UTC_SUFFIX = "Z"
REVIEW_STEP = "review"
APPROVE_STEP = "approve"
REVIEW_REQUEST = "review"
STATUS_APPROVED = "Approved"
STATUS_DRAFT = "Draft"
STATUS_UNPROCESSABLE = 422
EVENT_CREATED = "created"
EVENT_UPDATED = "updated"
EVENT_REVIEWED = "reviewed"
EVENT_APPROVED = "approved"
EVENT_REVISION = "revision_started"
LINK_SOURCE = "CHG"
LINK_TARGET = "REQ"
LINK_ROLE = "impacts"
SIGN_OFF_CASES_LIST = [(TEST_CASE_KIND, True), (DOCUMENT_KIND, True), (DESIGN_KIND, False)]
SIGN_OFF_CASES = [(index,) for index in range(len(SIGN_OFF_CASES_LIST))]
MSG_DOCS_REQ_METADATA = "the REQ docs list gives the requirement's type and origin"
MSG_CREATED_EVENT = "creating an artefact logs created"
MSG_UPDATED_EVENT = "editing a requirement logs updated"
MSG_REVIEW_FIELDS_REFUSED = "review fields set in an edit are refused with 422"
MSG_REVIEW_RECORDS = "the review sign-off records the reviewer and a UTC time"
MSG_REVIEW_LOGGED = "the review sign-off logs reviewed and no update"
MSG_APPROVE_LOGGED = "the approval sign-off logs approved"
MSG_STATUS_ONLY_APPROVED = "a status-only edit to Approved logs approved"
MSG_MIXED_EDIT_REFUSED = "an edit of content and status together is refused with 409"
MSG_REVISION_STARTED = (
    "an edit under an approved change goes back to Draft and logs updated and a revision"
)
REVIEW_SETUP_EXPECTED = [STATUS_OK, STATUS_CREATED, STATUS_CREATED]

SNAPSHOT_PREFIX = _letters(string.ascii_uppercase, 3, 3)
SNAPSHOT_READER_EMAIL = f"reader-{_letters(string.ascii_lowercase, 4, 8)}@example.com"
SNAPSHOT_READER_RULES = {"REQ": {"read": True, "all_origins": True}, "baseline": {"read": True}}
SNAPSHOT_REQUIREMENT_TITLE = f"Requirement {_letters(string.ascii_lowercase, 4, 10)}"
SNAPSHOT_DOCUMENT_TITLE = f"Document {_letters(string.ascii_lowercase, 4, 10)}"
SNAPSHOT_CAPTURED_DOCUMENTS = 1
MSG_SNAPSHOT_OPENS = "the reader opens the baseline"
MSG_SNAPSHOT_REQUIREMENT = "the requirement's record is shown"
MSG_SNAPSHOT_NO_DOCUMENT = "no document record is shown"
MSG_SNAPSHOT_COUNT = "the captured document count is kept"
MSG_SNAPSHOT_TITLE_HIDDEN = "the document's title is not shown"
MSG_SNAPSHOT_LIST = (
    "the list gives the baseline once with the requirement's public id and no records"
)

OUTBOUND_MARKER = datetime(2000, 1, 1)
OUTBOUND_DIRECTION = "bloom_to_jira"
OUTBOUND_SENT_TITLE = f"Defect {_letters(string.ascii_lowercase, 4, 10)}"
OUTBOUND_REFUSED_TITLE = f"Defect {_letters(string.ascii_lowercase, 4, 10)}"
OUTBOUND_FIRST_NUMBER = _draw.randrange(50_000, 60_000)
OUTBOUND_ISSUE_PATH = "/rest/api/3/issue"
OUTBOUND_CREATED_EVENT = "issue_created"
OUTBOUND_REFUSED_EVENT = "issue_create_refused"
MSG_OUTBOUND_BUG = "a new defect is sent to Jira as a Bug with its title as summary"
MSG_OUTBOUND_LINKED = "the sent defect links to the issue Jira created"
MSG_OUTBOUND_LOGGED = "the sent defect logs the issue it created"
MSG_OUTBOUND_REFUSED = "a defect Jira refuses stays unlinked and logs the refusal"

EXTERNAL_PROJECT_ID = _draw.randrange(1, 10_000)
EXTERNAL_USER_ID = _draw.randrange(1, 10_000)
EXTERNAL_EVERY_TYPE = None
EXTERNAL_NO_QUERY = 0
MSG_EXTERNAL_ADMIN_EVERY_TYPE = "an admin is limited to no document type"
MSG_EXTERNAL_ADMIN_NO_QUERY = "an admin's document types are answered without a database query"

LOG_CAPACITY = 10_000
APP_LOGGERS = ("bloom", "app")
INVITE_INFO_PATH = "/api/auth/invite-info"
ONE_TIME_TOKEN = _letters(string.ascii_letters + string.digits, 32, 40)
MSG_TOKEN_REQUEST_LOGGED = "the invite lookup request reaches the application log"
MSG_TOKEN_NOT_LOGGED = "the one-time token from the body or the query never reaches the log"

COMPOSE_FILE = "docker-compose.yml"
DOCKERFILE = "Dockerfile"
ENV_EXAMPLE = ".env.example"
COMPOSE_SERVICE = "bloom"
ATTACHMENT_DIR_VARIABLE = "BLOOM_ATTACHMENT_DIR"
ATTACHMENT_DIR = "/app/attachments"
ATTACHMENT_VOLUME = "bloom-attachments"
ATTACHMENT_MOUNT = f"{ATTACHMENT_VOLUME}:{ATTACHMENT_DIR}"
ATTACHMENT_MKDIR = f"mkdir -p {ATTACHMENT_DIR}"
ATTACHMENT_CHOWN = "chown -R appuser:appuser /app"
ATTACHMENT_EXAMPLE_LINE = f"{ATTACHMENT_DIR_VARIABLE}={ATTACHMENT_DIR}"
ATTACHMENT_WORDS = ("attachments", "appuser", "ATTACHMENT")
MSG_ATTACHMENT_DIR_SET = "the bloom service sets the attachment directory"
MSG_ATTACHMENT_MOUNTED = "the bloom service mounts the attachment volume on that directory"
MSG_ATTACHMENT_VOLUME_DECLARED = "the compose file declares the attachment volume"
MSG_ATTACHMENT_MKDIR = "the image creates the attachment mountpoint"
MSG_ATTACHMENT_CHOWN = "the image gives /app to appuser"
MSG_ATTACHMENT_EXAMPLE = "the example environment documents the attachment directory"

INVITE_TOKEN = "abc123"
INVITE_TOKEN_HASH = "6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090"
INVITE_OTHER_TOKEN = "different"
INVITE_PURPOSES = {
    "invite": "invite",
    "email_verification": "email_verification",
    "password_reset": "password_reset",
}
INVITE_VALID_HOURS = 1
INVITE_NOT_USED = None
MSG_INVITE_HASH_KNOWN = "a token hashes to its known SHA-256 digest"
MSG_INVITE_HASH_DIFFERS = "two different tokens hash differently"
MSG_INVITE_PURPOSE = "the token purpose keeps its stored value"
MSG_INVITE_UNUSED = "a new token is not marked used"
MSG_INVITE_NOT_EXPIRED = "a token expiring in an hour is still valid now"

EXTERNAL_MEMBERSHIP_ID = _draw.randrange(1, 10_000)
EXTERNAL_VISIBILITY = ("customer",)
EXTERNAL_GRANTED = ("REQ",)
EXTERNAL_GRANTED_TYPE = "REQ"
EXTERNAL_NOT_REFUSED = None
MSG_EXTERNAL_GRANTED_ALLOWED = "an external member may open the document type granted to them"

EXTERNAL_OTHER_TYPE = "TC"
EXTERNAL_REFUSAL_PATTERN = "[Nn]ot authorized"
MSG_EXTERNAL_OTHER_REFUSED = "an external member is refused a document type not granted to them"

EXTERNAL_ALLOWLIST = ("REQ", "TC")
EXTERNAL_ALLOWLIST_EXPECTED = {"REQ", "TC"}
MSG_EXTERNAL_ALLOWLIST = "an external member's document types are the types their term grants"

VISION_PREFIX = "PRJ"
VISION_DOCUMENTS = [
    ("PRJ-VIS-001", "VIS", "Vision"),
    ("PRJ-XYZ-001", "XYZ", "Unknown"),
]
VISION_AFTER_RESTART = [("VIS", "PRJ-VIS-001"), ("SPEC", "PRJ-SPEC-001")]
MSG_VISION_KEPT = "a restart keeps a Vision's kind and id and turns an unknown kind into SPEC"

STAMP_NAIVE = datetime(2026, 9, 27, 12, 34, 56, 789)
STAMP_AWARE = datetime(2026, 9, 27, 14, 34, tzinfo=timezone(timedelta(hours=2)))
STAMP_TEXT = "2026-09-27 12:34 UTC"
STAMP_NONE_TEXT = ""
STAMP_EXECUTED = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
STAMP_EXECUTED_STORED = datetime(2026, 9, 27, 12, 0)
STAMP_SERVER_ZONE = "Europe/Berlin"
MSG_STAMP_MINUTES = "a time is written in UTC to the minute"
MSG_STAMP_NONE = "a missing time is written as nothing"
MSG_STAMP_AWARE = "a time in another zone is written in UTC"
MSG_STAMP_EXECUTION_UTC = "an execution time is stored in UTC on a server in another zone"

RICH_CONTENT_TYPES = [
    "Requirement",
    "TestCase",
    "Document",
    "DesignItem",
    "RiskItem",
    "ChangeRequest",
    "TestConcept",
]
RICH_SCHEMA_SUFFIXES = ["Create", "Update", "Response"]
RICH_FIELDS = ["content_json", "content_html"]
RICH_TITLE_FIELDS = {"title", "name"}
RICH_TITLE = "Title"
RICH_FILLER = "x"
RICH_JSON = {"type": "doc", "content": []}
RICH_HTML = "<p>body</p>"
RICH_PAYLOAD = {"project_id": 1, "content_json": RICH_JSON, "content_html": RICH_HTML}
MSG_RICH_FIELD = "the schema carries the rich content field"
MSG_RICH_JSON = "the create schema keeps the editor's JSON content"
MSG_RICH_HTML = "the create schema keeps the editor's HTML content"

PYPROJECT = "pyproject.toml"
CLOUDRON_MANIFEST = "cloudron/CloudronManifest.json"
CLOUDRON_DESCRIPTION = "cloudron/DESCRIPTION.md"
CLOUDRON_CATALOG = "cloudron/CloudronVersions.json"
CLOUDRON_CHANGELOG = "cloudron/CHANGELOG"
CLOUDRON_TITLE = "Bloom PLM by EmbedLabs"
CLOUDRON_TAGLINE = "Requirements, controlled documents and traceability"
CLOUDRON_POSITIONING = (
    "Bloom PLM by EmbedLabs covers requirements, controlled documents, "
    "verification, risks, changes, defects, baselines and traceability."
)
CLOUDRON_RETIRED_WORDS = ("embedded", "self-hosted")
CLOUDRON_FILE_CHANGELOG = "file://"
CLOUDRON_PUBLISH_STATES = {"testing", "published"}
CLOUDRON_HEADER = r"^\[(\d+(?:\.\d+){0,2})[^\]]*\]$"
MSG_CLOUDRON_TITLE = "the manifest title is the product name"
MSG_CLOUDRON_TAGLINE = "the manifest tagline is the product tagline"
MSG_CLOUDRON_POSITIONING = "the description opens with the product positioning"
MSG_CLOUDRON_MANIFEST_WORD = "the manifest avoids a retired word"
MSG_CLOUDRON_DESCRIPTION_WORD = "the description avoids a retired word"
MSG_CLOUDRON_VERSION = "the manifest carries the product version"
MSG_CLOUDRON_UPSTREAM = "the manifest's upstream version is the product version"
MSG_CLOUDRON_CATALOG_VERSION = "the catalog entry carries the product version"
MSG_CLOUDRON_CATALOG_UPSTREAM = "the catalog entry's upstream version is the product version"
MSG_CLOUDRON_CATALOG_DESCRIPTION = "the catalog entry carries the description text"
MSG_CLOUDRON_CATALOG_CHANGELOG = "the catalog entry's changelog is inline, not a file link"
MSG_CLOUDRON_PUBLISH_STATE = "the catalog entry is in testing or published"
MSG_CLOUDRON_CHANGELOG_VERSION = "the changelog has a header for the product version"
MSG_CLOUDRON_CHANGELOG_TOP = "the changelog opens with a version header"
MSG_CLOUDRON_CHANGELOG_NEWEST = "the changelog's top version is at least the product version"

AUDIT_RETENTION_DAYS = 30
AUDIT_EVENTS = [("old", 40), ("new", 5)]
AUDIT_REMOVED = 1
AUDIT_LEFT = ["new"]
MSG_AUDIT_REMOVED = "the prune removes the one event older than the retention"
MSG_AUDIT_LEFT = "the event inside the retention is kept"

RESPONSE_PACKAGES = ("app.schemas", "app.api")
RESPONSE_SUFFIXES = ("Response", "Summary", "Item", "Entry", "Created")
RESPONSE_MIN_MODELS = 20
RESPONSE_API_PREFIX = "app.api."
RESPONSE_NONE_UNMARKED = []
MSG_RESPONSE_SCAN_COUNT = "the scan finds more than twenty response models"
MSG_RESPONSE_SCAN_API = "the scan finds response models inside app.api"
MSG_RESPONSE_UTC = "every timestamp of a response model has the UTC serializer"

STATUS_NO_CONTENT = 204
DELETE_PREFIXES = [
    first + _letters(string.ascii_uppercase, 2, 2)
    for first in _draw.sample(string.ascii_uppercase, 3)
]
DELETE_REQUIREMENT_TITLE = f"Requirement {_letters(string.ascii_lowercase, 4, 10)}"
MSG_DELETE_SIGN_IN = "the admin signs in"
MSG_DELETE_ANSWER = "the admin's delete is answered with no content"
MSG_DELETE_GONE = "the deleted project is no longer found"
MSG_DELETE_REQUIREMENT = "a requirement is created in the project"
MSG_DELETE_UNAUTHENTICATED = "a delete without a signed-in user is refused as unauthenticated"

STREAM_FILE = "attachment.txt"
STREAM_CHUNK = 3
STREAM_PAYLOAD = b"streamed attachment"
STREAM_SHA256 = hashlib.sha256(STREAM_PAYLOAD).hexdigest()
STREAM_OVERSIZE = b"too many bytes"
STREAM_OVERSIZE_LIMIT = 4
STREAM_FIRST_CHUNK = b"one"
STREAM_INTERRUPT_LIMIT = 8
STREAM_INTERRUPTIONS = ("OSError", "CancelledError")
STREAM_INTERRUPTED_READS = 2
STATUS_TOO_LARGE = 413
STREAM_NO_FILES = []
MSG_STREAM_CONTENT = "the stored file holds the streamed bytes"
MSG_STREAM_SIZE = "the stored size is the streamed size"
MSG_STREAM_SHA = "the stored checksum is the SHA-256 of the streamed bytes"
MSG_STREAM_NO_PARTS = "no partial file is left after a complete stream"
MSG_STREAM_TOO_LARGE = "an oversize stream is refused as too large"
MSG_STREAM_NO_TARGET = "an oversize stream leaves no stored file"
MSG_STREAM_CLEAN = "a failed stream leaves no file behind"
MSG_STREAM_ERROR = "the interruption reaches the caller"
MSG_STREAM_READS = "the stream stops at the interrupted second read"

SYNC_RESULT_EMPTY_CASE = {
    "last_execution_status": None,
    "last_executed_at": None,
    "last_execution_comment": None,
    "last_bud_run_id": None,
}
SYNC_RESULT_FAILED = {
    "status": "Failed",
    "executed_at": None,
    "comment": "Route endpoint returned fabricated polyline.",
    "bud_run_id": 5,
}
SYNC_RESULT_NEWER_CASE = {
    "last_execution_status": "Passed",
    "last_executed_at": datetime(2026, 7, 22, 12, 0, 0),
    "last_execution_comment": "newer",
    "last_bud_run_id": 8,
}
SYNC_RESULT_OLDER = {
    "status": "Failed",
    "executed_at": datetime(2026, 7, 22, 11, 0, 0),
    "comment": "older",
    "bud_run_id": 7,
}
SYNC_RESULT_TC_ID = "PRJ-TC-001"
SYNC_RESULT_STATUS = "Passed"
SYNC_RESULT_TOO_MANY = 1001
SYNC_RESULT_REFUSAL = "ValidationError"
MSG_SYNC_RESULT_APPLIED = "the latest result is applied to the test case"
MSG_SYNC_RESULT_STATUS = "the test case keeps the latest result's status"
MSG_SYNC_RESULT_COMMENT = "the test case keeps the latest result's comment"
MSG_SYNC_RESULT_RUN = "the test case keeps the latest result's Bud run"
MSG_SYNC_RESULT_TIME = "the test case gets an execution time"
MSG_SYNC_RESULT_OLDER = "an older result is not applied"
MSG_SYNC_RESULT_KEPT = "the newer execution stays on the test case"
MSG_SYNC_RESULT_BOUNDED = "a sync payload of more than 1000 results is refused"

IAM_ADMIN = "admin"
IAM_MAINTAINER = "maintainer"
IAM_VIEW_ONLY = {"REQ": {"view"}}
IAM_VIEW_AND_EDIT = {"REQ": {"view", "edit"}}
IAM_EDIT_REQUIREMENT = ("edit", "REQ")
IAM_PROJECT_LOOKUPS = 1
IAM_NOT_ASSIGNED = "not assigned"
IAM_MISSING_PERMISSION = "Missing permission"
MSG_IAM_ADMIN_ADMITTED = "an admin is admitted to a project without a membership"
MSG_IAM_ADMIN_NO_MEMBERSHIP = "an admin's admission returns no membership"
MSG_IAM_ADMIN_LOOKUP = "an admin's admission looks the project up once"
MSG_IAM_UNASSIGNED = "a user without access to the project is refused as not assigned"
MSG_IAM_MISSING_ACTION = "a user whose terms lack the action is refused with missing permission"
MSG_IAM_EXPLICIT_ACTION = "a user whose term grants the action is admitted"

IMPORT_PREFIXES = [
    first + _letters(string.ascii_uppercase, 2, 2)
    for first in _draw.sample(string.ascii_uppercase, 2)
]
IMPORT_USERS = [
    f"importer-{_letters(string.ascii_lowercase, 4, 8)}-{n}@example.com" for n in (1, 2)
]
IMPORT_ROLE = "admin"
IMPORT_COMPLETED = "completed"
IMPORT_STARTS_ALLOWED = 2
IMPORT_RETRY_SECONDS = "900"
MSG_IMPORT_FIRST = "the first import of the project starts"
MSG_IMPORT_ACTIVE = "a second import while one is active in the project is refused with 429"
MSG_IMPORT_STARTS = "an import start inside the user's limit starts"
MSG_IMPORT_LIMITED = "a start past the user's limit in 15 minutes is refused with 429"
MSG_IMPORT_RETRY = "the refusal asks to retry after 900 seconds"
MSG_IMPORT_COUNT = "only the allowed starts are recorded"
