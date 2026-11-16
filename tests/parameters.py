"""
* @file     ${tests/parameters.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Constants of Bloom's tests: drawn test data, expected values and messages.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Test data is drawn from SEED; BUDTEST_SEED repeats a run with the same data.
"""

import base64
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

SYNC_DATABASE = os.environ.get("BLOOM_SUITE_DATABASE") or "sqlite+aiosqlite:///:memory:"
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
CONFLICT_PATH = "/api/__flush_conflict__"
CONFLICT_ROUTE_NAME = "_flush_conflict"
CONFLICT_PREFIX_LETTER = "X"
CONFLICT_PHRASE = "already exists"
CONFLICT_DETAIL_KEY = "detail"
CONFLICT_REQUEST_ID_KEY = "request_id"
CONFLICT_LEAKS = ("projects_prefix_key", "INSERT INTO", "UniqueViolationError")
MSG_CONFLICT_STATUS = "two projects of one prefix flushed in one request are answered 409"
MSG_CONFLICT_PHRASE = "the detail says that it already exists"
MSG_CONFLICT_REQUEST_ID = "the answer carries a request id"
MSG_CONFLICT_QUOTES_ID = "the detail quotes the request id of the answer"
MSG_CONFLICT_NO_LEAK = "the answer does not contain {leak}"
REFRESH_COOKIE = "bloom_refresh_token"
REFRESH_COOKIE_FLAG = "HttpOnly"
REFRESH_COOKIE_PATH = "Path=/api/auth"
REFRESH_EMAIL_KEY = "email"
MSG_REFRESH_LOGIN = "the sign-in is answered 200"
MSG_REFRESH_COOKIE_SET = "the sign-in sets the refresh cookie"
MSG_REFRESH_HTTP_ONLY = "the refresh cookie is HttpOnly"
MSG_REFRESH_PATH = "the refresh cookie is limited to /api/auth"
MSG_REFRESH_OK = "a refresh with the cookie is answered 200"
MSG_REFRESH_ACCOUNT = "the refreshed access token reads the signed-in account"
MSG_REFRESH_NO_COOKIE = "a refresh without the cookie is refused with 401"
MSG_REFRESH_NEW_COOKIE = "a refresh sets a refresh cookie"
MSG_REFRESH_ROTATED = "the cookie after a refresh differs from the cookie before it"
MSG_REFRESH_REPLAY = "the cookie from before the refresh is refused with 401"
MSG_REFRESH_LOGOUT = "the sign-out is answered 200"
MSG_REFRESH_AFTER_LOGOUT = "the cookie of a signed-out session is refused with 401"
REPAIR_MIGRATION = "e1a7c3f9b204_repair_pre_baseline_schema.py"
REPAIR_COLUMN_COUNT = 1
REPAIR_TABLE_COLUMNS = 10
REPAIR_INDEX_COUNT = 1
MSG_REPAIR_UPGRADE = "the migrations reach head on a new database"
MSG_REPAIR_REPEAT = "the repair statements run a second time without an error"
MSG_REPAIR_COLUMN = "the repair restores integration_settings.account_email"
MSG_REPAIR_TABLE = "the repair restores change_request_sync_events with its 10 columns"
MSG_REPAIR_INDEX = "the repair restores the index on change_request_id"
REFUSAL_REQUESTS = 30
REFUSAL_ADDRESS = f"2001:db8::{_draw.randrange(1, 0xFFFF):x}:{_draw.randrange(1, 0xFFFF):x}"
REFUSAL_PORT = 4321
REFUSAL_PATH = "/api/projects"
REFUSAL_HEADERS = {"Authorization": "Bearer forged"}
REFUSAL_OUTCOME = "denied"
REFUSAL_ACTION = "security.repeated_refusals"
MSG_REFUSAL_STATUSES = "every request with a forged token is refused with 401"
MSG_REFUSAL_RECORDED = "every refused request is recorded as a denied api.request of the address"
MSG_REFUSAL_OVER_THRESHOLD = "the burst is larger than the refusal threshold"
MSG_REFUSAL_ONE_EVENT = "the burst leaves one security.repeated_refusals event for the address"
ASSIGNEE_BEFORE = "b7d3e91f4a26"
ASSIGNEE_PREFIX = _letters(string.ascii_uppercase, 3, 3)
ASSIGNEE_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
MSG_MIGRATION_BEFORE = "the migrations reach the revision before the one under test"
MSG_MIGRATION_HEAD = "the migrations reach head from the revision before"
MSG_MIGRATION_DOWNGRADE = "the downgrade reaches the revision before again"
MSG_ASSIGNEE_IS_CREATOR = "the existing workflow is assigned to its revision creator"
PARENT_BEFORE = "c4e8a2f6b1d3"
PARENT_PREFIX = _letters(string.ascii_uppercase, 3, 3)
PARENT_REQ_IDS = [f"{PARENT_PREFIX}-REQ-001", f"{PARENT_PREFIX}-REQ-002"]
MSG_PARENT_DROPPED = "after the upgrade both requirements remain and parent_id is gone"
MSG_PARENT_RESTORED = "after the downgrade both requirements remain and parent_id is back"
WIDENING_KIND = "REQ"
WIDENING_PREFIXES = ("PRJ", "ABC", "XYZ")
WIDENING_AT_BOUNDARY = ["PRJ-REQ-001", "PRJ-REQ-042", "PRJ-REQ-999"]
WIDENING_NEXT_AT_BOUNDARY = "PRJ-REQ-1000"
WIDENING_WIDENED = ["PRJ-REQ-0001", "PRJ-REQ-0042", "PRJ-REQ-0999"]
WIDENING_BELOW = ["ABC-REQ-001", "ABC-REQ-002"]
WIDENING_NEXT_BELOW = "ABC-REQ-003"
WIDENING_OTHER_TYPE = ["XYZ-REQ-999"]
WIDENING_TEST_CASE = "XYZ-TC-001"
MSG_WIDENING_NEXT = "the id after 999 is 1000"
MSG_WIDENING_STORED = "the ids already stored are rewritten with four digits"
MSG_WIDENING_BELOW_NEXT = "below 999 the next id keeps three digits"
MSG_WIDENING_BELOW_STORED = "below 999 the stored ids are not rewritten"
MSG_WIDENING_OTHER_TYPE = "widening the requirements leaves the test case id of the project alone"
SESSION_ROLE = "external"
SESSION_CHANGE_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
SESSION_RESET_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
SESSION_OLD_PASSWORD = _letters(string.ascii_letters + string.digits, 16, 24)
SESSION_NEW_PASSWORD = _letters(string.ascii_letters + string.digits, 16, 24)
SESSION_CHANGE = "change"
SESSION_RESET = "reset"
MSG_SESSION_BEFORE = "before the password {event} the access token reads the account"
MSG_SESSION_DONE = "the password {event} is answered 200"
MSG_SESSION_MAIL = "the reset mail carries a token"
MSG_SESSION_ACCESS = "the access token from before the password {event} is refused with 401"
MSG_SESSION_REFRESH = "the refresh cookie from before the password {event} is refused with 401"
MSG_SESSION_OLD_PASSWORD = "after the password {event} the old password is refused with 401"
MSG_SESSION_NEW_PASSWORD = "after the password {event} the new password signs in"
WORKFLOW_RACE_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
WORKFLOW_RACE_PREFIX = _letters(string.ascii_uppercase, 3, 3)
WORKFLOW_RACE_REQ_ID = f"{WORKFLOW_RACE_PREFIX}-REQ-001"
WORKFLOW_RACE_PATH = "/api/artefacts/requirement/{id}/workflow"
WORKFLOW_RACE_LOOKUP = "SELECT artefact_workflows."
WORKFLOW_RACE_WAIT = 0.25
WORKFLOW_RACE_FIRST_REVISION = 1
WORKFLOW_RACE_REVISION_KEY = "revision_number"
WORKFLOW_RACE_CREATOR_KEY = "creator"
WORKFLOW_RACE_ID_KEY = "id"
MSG_WORKFLOW_RACE_READS = "both first reads of the workflow are answered 200"
MSG_WORKFLOW_RACE_ONE = "two first reads at once store one workflow"
MSG_WORKFLOW_RACE_STATE = "the stored workflow is revision 1, a draft of the requirement's creator"
MSG_WORKFLOW_RACE_LATER = "a later read is answered 200"
MSG_WORKFLOW_RACE_REVISION = "the later read and the first reads show revision 1"
MSG_WORKFLOW_RACE_CREATOR = "the later read names the requirement's creator"
TOKEN_RACE_USES = 6
TOKEN_RACE_RESET_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
TOKEN_RACE_INVITE_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
TOKEN_RACE_VERIFY_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
TOKEN_RACE_USE = {
    "refresh": "refresh cookie",
    "reset": "password reset token",
    "invite": "invitation token",
    "verify": "verification token",
}
MSG_TOKEN_RACE_ISSUED = "the {token} is issued"
MSG_TOKEN_RACE_ONE = "of six uses of one {token} at once, one is answered 200"
MSG_TOKEN_RACE_OTHERS = "every other use of the {token} is refused with {status}"
LINK_BEFORE = "e1a7c3f9b204"
LINK_PREFIX = "PRJ"
LINK_REQ_IDS = ["PRJ-REQ-001", "PRJ-REQ-002"]
LINK_CONSTRAINT = "fk_artefact_links_allowed_triple"
LINK_FORBIDDEN = ("REQ", "REQ", "forbidden")
LINK_CORRECTED_ROLE = "refines"
LINK_OLD_ENDS = (1, 2)
LINK_NEW_ENDS = (2, 1)
LINK_REJECTED = [
    ("REQ", "REQ", "forbidden"),
    ("TC", "REQ", "references"),
    ("UNKNOWN", "REQ", "refines"),
]
LINK_ACCEPTED = [
    ("TCO", "PROT", "references"),
    ("PROT", "TCO", "implements"),
    ("REQ", "REQ", "references"),
    ("REQ", "REQ", "refines"),
]
LINK_LEGACY = ("derived_from", "derives_from")
LINK_TABLE = "artefact_links"
LINK_LEGACY_TABLE = "requirement_links"
LINK_REPORT_TABLE_KEY = "table"
LINK_CHECK_REFUSED = 1
LINK_CHECK_PASSED = 0
MSG_LINK_UNVALIDATED = "after the upgrade the link constraint is not validated"
MSG_LINK_KEPT = "the upgrade keeps the link with the forbidden triple"
MSG_LINK_REJECTED = "a new link {triple} is refused by the constraint"
MSG_LINK_ACCEPTED = "a new link {triple} is stored"
MSG_LINK_TABLE_IS_CODE = "the allowed triples in the database are the triples of the code"
MSG_LINK_CHECK_REFUSED = "the check answers 1 while a forbidden link exists"
MSG_LINK_REPORT_INVALID = "the report names the forbidden link with its role"
MSG_LINK_REPORT_LEGACY = "the report maps the legacy requirement link to its new role"
MSG_LINK_STILL_UNVALIDATED = "the refused check leaves the constraint not validated"
MSG_LINK_CHECK_PASSED = "the check answers 0 once the link has an allowed role"
MSG_LINK_VALIDATED = "the passed check validates the constraint"
MSG_LINK_COUNTS = "one requirement link and one artefact link remain"
LEGACY_CHANGE_ID = "PRJ-CHG-001"
LEGACY_CHANGE_STATUS = "Implemented"
LEGACY_REQUIREMENT_STATUS = "Approved"
LEGACY_BASELINE_NAME = "Frozen"
LEGACY_SNAPSHOT = '{"legacy": true}'
WORKFLOW_SCHEMA_ASPECTS = {
    "columns": "column names",
    "types": "column types and nullability",
    "primary": "primary keys",
    "unique": "unique constraints",
    "foreign": "foreign keys",
    "checks": "check constraints",
    "pending": "pending-request index",
    "comments": "comment columns and their request key",
}
WORKFLOW_PENDING_INDEX = "uq_artefact_requests_pending_cycle"
WORKFLOW_PENDING_COLUMNS = ["workflow_id", "revision_number", "kind"]
WORKFLOW_PENDING_WHERE = "status='pending'"
WORKFLOW_COMMENT_COLUMNS = ("revision_number", "content_hash", "review_request_id")
WORKFLOW_COMMENT_KEY = (["review_request_id"], "artefact_requests", "SET NULL")
MSG_WORKFLOW_SCHEMA_COMPARED = "the {aspect} of the workflow tables were compared"
MSG_WORKFLOW_SCHEMA = "the migrated {aspect} equal the models"
MSG_LEGACY_REQUIREMENTS = "the upgrade leaves every requirement status as it was"
MSG_LEGACY_CHANGE = "the upgrade leaves the change request status as it was"
MSG_LEGACY_BASELINE = "the upgrade leaves the baseline snapshot as it was"
MSG_LEGACY_NO_WORKFLOWS = "the upgrade creates no workflow, revision or request"
OVERLAP_BEFORE = "8134a1512496"
OVERLAP_PREFIX = _letters(string.ascii_uppercase, 3, 3)
OVERLAP_PEOPLE = [
    f"{_letters(string.ascii_lowercase, 5, 8)}{index}@example.com" for index in range(4)
]
OVERLAP_BUNDLE = "Developers"
OVERLAP_SECOND_BUNDLE = "Testers"
OVERLAP_POLICY = "Read Customer"
OVERLAP_KEPT = ("entries", "policies", "roles")
OVERLAP_REFUSAL = "overlapping project groups"
MSG_OVERLAP_KEPT = "the upgrade keeps every access entry, entry policy and account role"
MSG_OVERLAP_STORED = "a second group for a person who holds one in the project is stored"
MSG_OVERLAP_DUPLICATE = "the same group for the same person a second time is refused"
MSG_OVERLAP_PLAIN = "a second entry without a group for a person is refused"
MSG_OVERLAP_REFUSED = "the downgrade is refused while a person holds two groups in a project"
MSG_OVERLAP_REFUSAL_TEXT = "the refusal names the overlapping project groups"
MSG_OVERLAP_UNCHANGED = "the refused downgrade changes no row, index or revision"
MSG_OVERLAP_DOWNGRADED = "after the downgrade the database is as it was before the upgrade"
MSG_OVERLAP_UPGRADED_AGAIN = "after the second upgrade the database is as it was after the first"
MSG_MIGRATION_HEAD_AGAIN = "the migrations reach head a second time"
VISIONS_BEFORE = "d1f6b8a3e572"
VISIONS_PREFIX = "PRJ"
VISIONS_DOC_ID = "PRJ-VIS-001"
VISIONS_POLICY = "Visions"
VISIONS_KIND = "VIS"
VISIONS_SPEC_KIND = "SPEC"
VISIONS_SPEC_POLICY = "Specifications"
VISIONS_RELEASED_SET = (
    "Requirements",
    "Specifications",
    "Standards",
    "Designs",
    "Risks",
    "Change Requests",
    "Concepts",
    "Test Cases",
    "Suites",
    "Campaigns",
    "Defects",
    "Protocols",
    "Reports",
    "Baselines",
    "Parameters",
    "Traceability",
    "Project Management",
)
VISIONS_COVERED = (
    "Read Internal",
    "Read Customer",
    "Review Internal",
    "Review Customer",
    "Application Administration",
)
VISIONS_HOLDERS = {
    "released": f"{_letters(string.ascii_lowercase, 5, 8)}@example.com",
    "spec_only": f"{_letters(string.ascii_lowercase, 5, 8)}@example.com",
}
VISIONS_GROUP = "Spec Writers"
VISIONS_OWNERS = "Product Owners"
VISIONS_EDITABLE = "Hand made"
VISIONS_UNTOUCHED = ("spec_only", "group", "editable", "group_row")
VISIONS_DEFAULT = [("document", True)]
VISIONS_REFUSAL = "Cannot downgrade below 637f976e78e0"
MSG_VISIONS_ABSENT = "before the upgrade no Visions policy exists"
MSG_VISIONS_RELEASED = "the entry holding the released maintainer set gains Visions"
MSG_VISIONS_OWNERS = "the Product Owners group gains Visions"
MSG_VISIONS_UNTOUCHED = (
    "the Specifications-only entry, its group and the hand-made policy are as before"
)
MSG_VISIONS_DEFAULT = "Visions is one default document policy"
MSG_VISIONS_COVERED = "the five read, review and administration policies are the ones extended"
MSG_VISIONS_AS_SPEC = "{policy} gives visions what it gives specifications"
MSG_VISIONS_REST = "{policy} keeps every other permission it had"
MSG_VISIONS_REFUSED = "the downgrade is refused while a vision exists"
MSG_VISIONS_REFUSAL_TEXT = "the refusal names the revision it cannot go below"
MSG_VISIONS_DOWNGRADED = "after the downgrade every row is as it was before the upgrade"
MSG_VISIONS_AGAIN = "after the second upgrade the released entry holds the same policies"
EMAIL_SELF_OLD = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_SELF_NEW = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_MEMBER_OLD = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_MEMBER_NEW = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_STALE_OLD = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_STALE_APPROVED = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_STALE_OTHER = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_GUARD = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_GUARD_NEW = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_ADMIN_OLD = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_ADMIN_NEW = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_INVITED = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EMAIL_ADMIN_ROLE = "admin"
EMAIL_AUTHORIZATION_SENDER = "send_email_change_authorization_email"
EMAIL_CHANGE_SENDER = "send_email_change_email"
EMAIL_INVITE_SENDER = "send_invite_email"
EMAIL_SENDER_KEY = "sender"
EMAIL_TO_KEY = "to_email"
EMAIL_AWAITING_CURRENT = "awaiting_current_confirmation"
EMAIL_AWAITING = "awaiting_confirmation"
EMAIL_REQUESTED = "requested"
EMAIL_CURRENT_PHRASE = "current email"
EMAIL_NEW_PHRASE = "new email"
EMAIL_MOVED = (401, 401, 401, 200)
MSG_EMAIL_REQUEST = "the email change request is answered 200"
MSG_EMAIL_SELF_PHRASE = "the answer tells the administrator to confirm from the current email"
MSG_EMAIL_SELF_PENDING = "the account keeps its email and waits for the current mailbox"
MSG_EMAIL_SELF_MAIL = "one mail goes out, to the current address, asking to authorize the change"
MSG_EMAIL_AUTHORIZED = "the confirmation from the current mailbox is answered 200"
MSG_EMAIL_NEW_PHRASE = "the answer tells the administrator to confirm from the new email"
MSG_EMAIL_SELF_WAITING = "the account keeps its email and waits for the new mailbox"
MSG_EMAIL_NEW_MAIL = "one mail goes out, to the new address, after the current mailbox confirmed"
MSG_EMAIL_CONFIRMED = "the confirmation from the new mailbox is answered 200"
MSG_EMAIL_MOVED = (
    "the old access token, refresh cookie and email are refused, and the new email signs in"
)
MSG_EMAIL_NO_MAIL = "a member's request sends no mail before an administrator approves"
MSG_EMAIL_REQUESTED = "the member's change waits as requested"
MSG_EMAIL_APPROVED = "the administrator's approval is answered 200"
MSG_EMAIL_APPROVAL_MAIL = "the approval mails the confirmation naming the old and the new address"
MSG_EMAIL_AWAITING = "after the approval the account keeps its email and waits for confirmation"
MSG_EMAIL_NOT_YET = "before the confirmation the new email is refused and the old one signs in"
MSG_EMAIL_AFTER = "after the confirmation the account has the new email and no pending change"
MSG_EMAIL_VERIFIED = "the confirmed address is recorded as verified"
MSG_EMAIL_STALE = (
    "a token approved for one address is refused with 400 once another address is pending"
)
MSG_EMAIL_STALE_LOGINS = "after the refused token only the old email signs in"
MSG_EMAIL_WRONG_PASSWORD = "a request with a wrong current password is refused with 400"
MSG_EMAIL_NOT_STARTED = "the refused request leaves no pending email"
MSG_EMAIL_BYPASS = "the general account update refuses an email with 422"
MSG_EMAIL_ADMIN_STARTED = (
    "an administrator's change is answered 200, keeps the email and waits for confirmation"
)
MSG_EMAIL_ADMIN_MOVED = "after the confirmation the old email is refused and the new one signs in"
MSG_EMAIL_INVITED = "the invitation is accepted with 200 and asks for no email verification"
MSG_EMAIL_INVITED_SIGN_IN = "the invited account signs in"
MSG_EMAIL_INVITED_VERIFIED = "the invited account's address is recorded as verified"

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

DOC_KIND_LEGACY = [
    ("DOC", "SPEC"),
    ("Specification", "SPEC"),
    ("Protocol", "PRT"),
    ("Report", "RPT"),
    ("External Standard", "STD"),
    (None, "SPEC"),
]
DOC_KIND_ACCEPTED = ["SPEC", "PRT"]
DOC_KIND_REFUSED = ["Protocol", "DOC", "OTHER", None]
DOC_KIND_REFUSAL_PHRASES = ["Supported shared-document kinds", "not accepted on the public API"]
STATUS_UNPROCESSABLE_ENTITY = 422
DOC_KIND_SLUGS = [
    ("specifications", "SPEC"),
    ("protocols", "PRT"),
    ("reports", "RPT"),
    ("standards", "STD"),
]
DOC_KIND_LINK_PROJECT = 7
DOC_KIND_LINK_TYPE = "SPEC"
DOC_KIND_INCOMING = [(10, 2, 1)]
DOC_KIND_OUTGOING = [(10, 3, 2)]
DOC_KIND_LINK_COUNTS = {10: {"incoming": 2, "outgoing": 3, "suspect": 3}}
MSG_DOC_KIND_LEGACY = "a legacy document kind maps to its canonical code"
MSG_DOC_KIND_ACCEPTED = "a canonical document kind is accepted as it is"
MSG_DOC_KIND_REFUSED = "a non-canonical document kind is refused with 422"
MSG_DOC_KIND_REFUSAL_TEXT = "the refusal names the supported kinds and the refused wire values"
MSG_DOC_KIND_SLUG = "a shared-document route slug maps to its kind"
MSG_DOC_KIND_LINKS = "the link counts add incoming and outgoing suspect links"

NAMING_PROJECT = {"name": "Demo", "prefix": " prj "}
NAMING_PREFIX = "PRJ"
NAMING_BAD_PREFIXES = ["BLOOM", "PR1", "PRJ-1", "PRJ REQ", "1VCU", "VCU_REQ", "PRJ.REQ"]
NAMING_BAD_UPDATE = {"prefix": "PRJ-REQ-001"}
NAMING_REFUSAL = "ValidationError"
NAMING_REQUIREMENT = {"project_id": 1, "title": "Title"}
NAMING_TEST_CASE = {"project_id": 1, "title": "TC Title"}
NAMING_DOCUMENT = {"project_id": 1, "title": "Spec", "doc_type": "SPEC"}
NAMING_OTHERS = {
    "DesignItemCreate": ("design_id", {"project_id": 1, "title": "D"}),
    "RiskItemCreate": ("risk_id", {"project_id": 1, "title": "R"}),
    "ChangeRequestCreate": ("change_id", {"project_id": 1, "title": "C"}),
    "TestConceptCreate": ("concept_id", {"project_id": 1, "name": "N"}),
}
MSG_NAMING_PREFIX = "a project prefix is trimmed and upper-cased"
MSG_NAMING_BAD_PREFIX = "a prefix that would break generated ids is refused"
MSG_NAMING_BAD_UPDATE = "a project update refuses an invalid prefix"
MSG_NAMING_FIELD_KEPT = "the create schema keeps the given field"
MSG_NAMING_NO_CLIENT_ID = "the create schema takes no client-chosen public id"
MSG_NAMING_BUILDS = "the create schema builds without a public id"

START_SCRIPT = "docker/start.sh"
SUPERVISORD_CONF = "docker/supervisord.conf"
START_HANDOVER = 'exec gosu "$APP_USER" /usr/local/bin/supervisord -c /etc/supervisord.conf'
START_APP_USER = "APP_USER=appuser"
START_FD_LOOP = "for fd in 1 2; do"
START_FD_TEST = 'if ! gosu "$APP_USER" test -w "/proc/self/fd/$fd"; then'
START_FD_CHOWN = 'chown "$APP_UID:$APP_GID" "/proc/self/fd/$fd"'
START_CLOUDRON_IF = 'if [ -n "${CLOUDRON_APP_ORIGIN:-}" ]; then'
START_ELSE = "\nelse\n"
START_FI = "\nfi\n"
START_DATA_CHOWN = 'chown -R "$APP_UID:$APP_GID" /app/data'
START_SECRETS = "secrets_file=/app/data/secrets.env"
START_MIGRATION = 'gosu "$APP_USER" alembic upgrade head'
START_ATTACHMENT_CHOWN = 'chown "$APP_UID:$APP_GID" /app/attachments'
START_RECURSIVE = "chown -R"
START_ROOT_SETTING = "user=root"
START_PIDFILE = "pidfile=/run/bloom/supervisord.pid"
START_USER_ROOT = r"(?m)^USER root$"
START_NGINX_USER = "user appuser;"
START_NGINX_USER_DROP = "-e '/^[[:space:]]*user[[:space:]]/d'"
START_HANDOVERS = 1
MSG_START_LAST = "start.sh ends by handing supervisord to appuser"
MSG_START_ONCE = "start.sh hands over to supervisord exactly once"
MSG_START_APP_USER = "start.sh runs its processes as appuser"
MSG_START_FD = "start.sh gives the container output to appuser when it cannot write to it"
MSG_START_FD_FIRST = "the output descriptors are fixed before the handover"
MSG_START_DATA = "on Cloudron start.sh gives every file under /app/data to appuser"
MSG_START_DATA_FIRST = "the data chown runs before the secrets and the migrations"
MSG_START_LOCAL = "outside Cloudron start.sh gives the attachment directory to appuser"
MSG_START_LOCAL_FLAT = "outside Cloudron no recursive chown runs"
MSG_START_NOT_ROOT = "supervisord has no root user setting"
MSG_START_PIDFILE = "supervisord keeps its pid file in the appuser runtime folder"
MSG_START_USER_ROOT = "the image starts as root for the preparation"
MSG_START_NGINX_USER = "nginx.conf keeps no user directive"
MSG_START_NGINX_DROP = "the image build drops nginx's user directive"

HTTP_HEALTH = "/api/health"
HTTP_READY = "/api/ready"
HTTP_ROOT = "/"
HTTP_OPENAPI = "/api/openapi.json"
HTTP_LOGIN = "/api/auth/login"
HTTP_ME = "/api/auth/me"
HTTP_PROJECTS = "/api/projects"
HTTP_LINKS = "/api/links"
HTTP_HEALTHY = "healthy"
HTTP_READY_STATUS = "ready"
HTTP_CONNECTED = "connected"
HTTP_PRODUCT = "Bloom PLM by EmbedLabs"
HTTP_VERSION_KEY = "version"
HTTP_WRONG_PASSWORD = _letters(string.ascii_letters + string.digits, 24, 32)
HTTP_SOME_PROJECT = 1
HTTP_MISSING_PROJECT = 999_999_999
MSG_HTTP_HEALTH_OK = "the health probe answers 200"
MSG_HTTP_HEALTHY = "the health probe reports healthy"
MSG_HTTP_HEALTH_VERSION = "the health probe carries the version"
MSG_HTTP_HEALTH_NO_DB = "the health probe does not inspect the database"
MSG_HTTP_ROOT_OK = "the root answers 200"
MSG_HTTP_ROOT_PRODUCT = "the root names the product"
MSG_HTTP_ROOT_VERSION = "the root carries the version"
MSG_HTTP_READY_OK = "the ready probe answers 200"
MSG_HTTP_READY = "the ready probe reports ready"
MSG_HTTP_READY_DB = "the ready probe confirms the database"
MSG_HTTP_OPENAPI_HIDDEN = "the OpenAPI document is hidden while docs are off"
MSG_HTTP_WRONG_PASSWORD = "a wrong password is refused with 401"
MSG_HTTP_PROJECTS_AUTH = "the project list needs a signed-in user"
MSG_HTTP_LINKS_AUTH = "the link list needs a signed-in user"
MSG_HTTP_LOGIN = "the admin signs in"
MSG_HTTP_ME = "the signed-in admin reads their own account"
MSG_HTTP_ME_EMAIL = "the account is the admin's"
MSG_HTTP_PROJECTS = "the signed-in admin lists projects"
MSG_HTTP_PROJECTS_LIST = "the project list is a list"
MSG_HTTP_LINKS_MISSING = "the links of a missing project answer 404"

PERM_ANY = "*"
PERM_ADMIN_ROLES = ("admin", None)
PERM_UNASSIGNED_ROLES = ("maintainer", None)
PERM_MAINTAINER_ROLES = ("maintainer", "maintainer")
PERM_MERGE_ROLES = ("external", "external")
PERM_ADMIN_BASELINE = {PERM_ANY: {PERM_ANY}}
PERM_NO_BASELINE = {}
PERM_MAINTAINER_CHECK = ("delete", "REQ")
PERM_MEMBER_RESOURCE = "member"
PERM_READER_ROLES = [
    ("external", "external"),
    ("maintainer", "external"),
    ("external", "maintainer"),
]
PERM_READER_CHECKS = [
    ("view", "REQ", True),
    ("comment", "TC", True),
    ("edit", "REQ", False),
    ("view", "parameter", False),
]
PERM_MERGES = [{"TC": ["create"], "baseline": ["approve"]}, None]
PERM_MERGE_CHECKS = [
    ("create", "TC", True),
    ("view", "TC", True),
    ("approve", "baseline", True),
    ("create", "REQ", False),
]
PERM_WILDCARDS = [
    ({PERM_ANY: {"view"}}, "view", "DES", True),
    ({PERM_ANY: {"view"}}, "edit", "DES", False),
    ({"DES": {PERM_ANY}}, "approve", "DES", True),
    ({}, "view", "DES", False),
]
PERM_TRANSITIONS = [
    ("Draft", "Review", "edit"),
    ("Review", "Draft", "review"),
    ("Analysis", "Implemented", "review"),
    ("Review", "Approved", "approve"),
    ("Submitted", "Rejected", "approve"),
    ("Open", "Closed", "edit"),
]
PERM_VALID_MATRIX = {"REQ": ["view"], PERM_ANY: [PERM_ANY], "link": ["create"]}
PERM_INVALID_MATRIX = {"widget": ["view"], "DES": ["fly"], "RSK": "view"}
PERM_INVALID_MESSAGES = [
    "unknown resource 'widget'",
    "unknown action 'fly' on 'DES'",
    "actions for 'RSK' must be a list",
]
PERM_LISTS_INPUT = {"RSK": {"view", "edit"}, PERM_ANY: {"view"}}
PERM_LISTS = {PERM_ANY: ["view"], "RSK": ["edit", "view"]}
PERM_MEMBER_MATRIX = {"member": ["view"], "REQ": ["manage"]}
PERM_MEMBER_MESSAGES = ["unknown resource 'member'", "unknown action 'manage' on 'REQ'"]
MSG_PERM_ADMIN = "an admin's baseline grants every action on every resource"
MSG_PERM_NO_MEMBERSHIP = "a maintainer without membership has no baseline"
MSG_PERM_MAINTAINER_RESOURCES = "a project maintainer's baseline covers every resource"
MSG_PERM_MAINTAINER_DELETE = "a project maintainer may delete requirements"
MSG_PERM_NO_MEMBER_RESOURCE = "project members are not a permission resource"
MSG_PERM_READER = "a reader's baseline grants viewing and commenting only"
MSG_PERM_MERGE = "merging policies only adds actions"
MSG_PERM_WILDCARD = "the wildcard stands for every resource or every action"
MSG_PERM_TRANSITION = "a status transition needs its action"
MSG_PERM_VALID = "a valid matrix has no invalid entries"
MSG_PERM_INVALID = "unknown resources, unknown actions and non-lists are named"
MSG_PERM_LISTS = "permissions turn into sorted lists"
MSG_PERM_MEMBERS = "project members and manage are not in the vocabulary"

LINK_NORMALIZED = [("req", "REQ"), ("spec", "SPEC")]
LINK_ROLES = [
    ("TC", "REQ", ("verifies",)),
    ("DES", "REQ", ("satisfies", "implements", "references")),
    ("TC", "DES", ()),
    ("CPT", "TC", ("implements",)),
    ("CPT", "SPEC", ("covers", "verifies", "references")),
    ("CPT", "REQ", ("covers", "verifies", "references")),
    ("REQ", "SPEC", ("derives_from", "refines", "references")),
    ("SPEC", "REQ", ()),
    ("CMP", "REQ", ("covers", "references")),
    ("CMP", "SPEC", ("verifies", "references")),
    ("TS", "REQ", ("covers", "references")),
    ("TS", "TC", ("contains", "references")),
]
LINK_KNOWN = [("TC", True), ("STD", True), ("TS", True), ("other", False)]
LINK_ROLE_CHECKS = [
    ("TC", "REQ", "verifies", True),
    ("TC", "REQ", "references", False),
    ("TC", "DES", "relates_to", False),
    ("CPT", "TC", "implements", True),
    ("TS", "TC", "contains", True),
    ("CMP", "REQ", "verifies", False),
    ("SPEC", "REQ", "references", False),
    ("REQ", "REQ", "references", False),
    ("REQ", "DES", "references", False),
]
LINK_TAG_HOSTS = [
    (kind, True) for kind in ("REQ", "DES", "RSK", "CHG", "CPT", "SPEC", "PRT", "RPT", "STD")
] + [(kind, False) for kind in ("TC", "TS", "CMP", "DEF", "other")]
LINK_TAG_PAIRS = [
    ("SPEC", "REQ", True),
    ("REQ", "REQ", True),
    ("REQ", "DES", True),
    ("REQ", "CMP", True),
    ("REQ", "TS", True),
    ("REQ", "TC", True),
    ("CMP", "REQ", False),
    ("TS", "REQ", False),
    ("TC", "REQ", False),
    ("REQ", "other", False),
    ("other", "REQ", False),
]
MSG_LINK_NORMALIZED = "a linkable kind is normalized to its code"
MSG_LINK_ROLES = "a kind pair allows exactly the roles of its matrix row"
MSG_LINK_KNOWN = "only supported kinds are linkable"
MSG_LINK_ROLE = "a role is allowed only on the pairs whose matrix row lists it"
MSG_LINK_TAG_HOST = "only prose bodies host tags"
MSG_LINK_TAG_PAIR = "tags reach any known kind from a tag host, outside the link matrix"

BULK_GROUP_NAMES = [f"Group {_letters(string.ascii_lowercase, 4, 8)} {n}" for n in range(8)]
BULK_POLICY_NAME = f"Policy {_letters(string.ascii_lowercase, 4, 8)}"
BULK_POLICY_RULES = {"REQ": {"read": True, "visibility": ["customer"]}}
BULK_EMAILS = [f"member-{_letters(string.ascii_lowercase, 4, 8)}-{n}@example.com" for n in range(8)]
BULK_EXTERNAL = "external"
BULK_MAINTAINER = "maintainer"
BULK_UNKNOWN_USER = 2_147_483_647
BULK_INVALID_SELECTIONS = [[], [1, 1], [0], [-1]]
BULK_NO_GRANTS = []
BULK_NO_MEMBERS = []
MSG_BULK_ADDED = "a bulk membership request is created"
MSG_BULK_MEMBERS = "the group holds exactly the requested users"
MSG_BULK_POLICIES = "the bulk request leaves the group's policies unchanged"
MSG_BULK_GRANTS = "the bulk request admits the group to no project"
MSG_BULK_UNKNOWN = "a bulk request naming an unknown user is refused with 404"
MSG_BULK_NONE_ADDED = "a refused bulk request adds nobody"
MSG_BULK_INVALID = "an empty, repeated or non-positive selection is refused with 422"
MSG_BULK_SINGLE = "a single member is added"
MSG_BULK_RETAINED = "a bulk request keeps existing members and adds the rest"
MSG_BULK_REPEATED = "repeating a bulk request is accepted"
MSG_BULK_DUPLICATE = "adding an existing member alone is still a conflict"
MSG_BULK_ADMIN_ONLY = "only an administrator may add members in bulk"

SQLITE_FOREIGN_KEYS = "PRAGMA foreign_keys=ON"
DELETION_EMAILS = [
    f"deleteme-{_letters(string.ascii_lowercase, 4, 8)}-{n}@example.com" for n in (1, 2)
]
DELETION_ROLE = "external"
DELETION_PREFIX = _letters(string.ascii_uppercase, 3, 3)
DELETION_POLICY = f"Policy {_letters(string.ascii_lowercase, 4, 8)}"
DELETION_PERMISSIONS = {"*": ["view", "comment"]}
DELETION_VISIBILITY = "customer"
DELETION_DOC_TYPES = ["REQ", "TC", "CPT", "CMP"]
DELETION_ACCEPTED = [STATUS_OK, STATUS_CREATED]
MSG_DELETION_CREATED = "the user is created"
MSG_DELETION_MEMBER = "the user becomes a project member"
MSG_DELETION_ANSWER = "the delete is answered with no content"
MSG_DELETION_LISTED = "the user list answers"
MSG_DELETION_GONE = "the deleted user is no longer listed"

PASSWORD_VALID = "correct horse battery"
PASSWORD_SHORT = "short"
PASSWORD_FILLER = "x"
PASSWORD_SHORT_LENGTHS = ("none", "one", "one below the minimum")
PASSWORD_OVERLONG = "a"
PASSWORD_MULTIBYTE = "é" * 37
PASSWORD_TOO_SHORT = "at least"
PASSWORD_TOO_LONG = "too long"
PASSWORD_SCHEMAS = {
    "UserCreate": ("password", {"email": "u@example.com", "full_name": "U"}),
    "PasswordChange": ("new_password", {"current_password": "whatever-old"}),
    "AcceptInviteRequest": ("password", {"token": "t"}),
    "ResetPasswordRequest": ("new_password", {"token": "t"}),
}
PASSWORD_REFUSAL = "ValidationError"
MSG_PASSWORD_MINIMUM = "a password of exactly the minimum length is accepted"
MSG_PASSWORD_SHORT = "a password below the minimum length is refused"
MSG_PASSWORD_LONG = "a password over the byte limit is refused"
MSG_PASSWORD_MULTIBYTE_LENGTH = "the multibyte password has fewer characters than the byte limit"
MSG_PASSWORD_SCHEMA_SHORT = "every password entry point refuses a short password"
MSG_PASSWORD_SCHEMA_VALID = "every password entry point keeps a valid password"

CREATE_ID_PREFIX = _letters(string.ascii_uppercase, 3, 3)
CREATE_ID_CASES = [
    ("/api/requirements", {"title": "Requirement"}, "req_id", "REQ"),
    ("/api/test-cases", {"title": "Test case"}, "tc_id", "TC"),
    (
        "/api/projects/{project_id}/documents",
        {"title": "Specification", "doc_type": "SPEC"},
        "doc_id",
        "SPEC",
    ),
]
MSG_CREATE_ID_CREATED = "the artefact is created without a client-supplied id"
MSG_CREATE_ID_PATTERN = "the assigned public id follows the id pattern"
MSG_CREATE_ID_PREFIX = "the assigned public id starts with the project prefix and type code"
MSG_CREATE_ID_SHAPE = "the assigned public id is prefix, type code and a three-digit number"

LOOKUP_PREFIX = "PRJ"
LOOKUP_ADMIN = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
LOOKUP_REQUIREMENT = {"req_id": "PRJ-REQ-001", "title": "Login works", "status": "Approved"}
LOOKUP_TEST_CASE = {"tc_id": "PRJ-TC-001", "title": "Verify login"}
LOOKUP_DEFECT = {"defect_id": "PRJ-DEF-001", "title": "Login broken"}
LOOKUP_ROLE = "relates"
LOOKUP_ADMIN_ROLE = "admin"
LOOKUP_KINDS = ("REQ", "TC", "DEF")
LOOKUP_TEST_CASE_TYPE = "test-case"
LOOKUP_DEFECT_TYPE = "defect"
LOOKUP_TEST_CASE_FIELD = "tc_id"
LOOKUP_UNKNOWN = "PRJ-TC-999"
MSG_LOOKUP_PUBLIC = "a test case is found by its public id"
MSG_LOOKUP_DATABASE = "a test case is still found by its database id"
MSG_LOOKUP_UNKNOWN = "an unknown public id answers 404"
MSG_LOOKUP_SAME_BACKLINKS = "a defect's backlinks are the same by public id and by database id"
MSG_LOOKUP_BACKLINK = "the defect's backlinks name the linked requirement"

VARIABLE_ITEM = {
    "id": 42,
    "project_id": 7,
    "kind": "variable",
    "key": "API_URL",
    "value": "https://old.example.com",
    "description": "old description",
}
VARIABLE_UPDATE = {
    "kind": "parameter",
    "key": "API_BASE_URL",
    "value": "https://new.example.com",
    "description": None,
}
VARIABLE_DUPLICATE = {"id": 43, "project_id": 7, "kind": "parameter", "key": "API_BASE_URL"}
VARIABLE_DUPLICATE_UPDATE = {"kind": "parameter", "key": "API_BASE_URL"}
VARIABLE_DUPLICATE_DETAIL = "Variable key already exists in this project"
VARIABLE_ONE_WRITE = 1
VARIABLE_NO_WRITE = 0
MSG_VARIABLE_SAME_ITEM = "the update answers with the variable it changed"
MSG_VARIABLE_FIELD = "the update writes the field it was given"
MSG_VARIABLE_FLUSHED = "the update flushes once"
MSG_VARIABLE_REFRESHED = "the update refreshes the changed variable once"
MSG_VARIABLE_DUPLICATE = "a duplicate kind and key in the project is refused with 400"
MSG_VARIABLE_DUPLICATE_DETAIL = "the refusal names the duplicate key"
MSG_VARIABLE_NOT_WRITTEN = "a refused update writes nothing"

API_PREFIX = "/api"
ROUTE_PUBLIC_ENDPOINTS = {
    "health_check",
    "readiness_check",
    "get_version",
    "prometheus_metrics",
    "login",
    "refresh",
    "logout",
    "get_invite_info",
    "accept_invite",
    "verify_email",
    "forgot_password",
    "reset_password",
    "confirm_email_change",
    "setup_status",
    "create_first_admin",
    "cli_start",
    "cli_exchange",
    "cli_refresh",
}
ROUTE_SIGNED_WEBHOOKS = {"github_webhook", "gitlab_webhook", "jira_webhook"}
ROUTE_AUTH_DEPENDENCIES = {
    "get_current_user",
    "require_admin",
    "require_bud_sync_token",
    "role_checker",
}
MSG_ROUTE_BOUNDARY = (
    "every API route outside the public and signed webhook lists needs a signed-in caller"
)
MSG_ROUTE_WEBHOOKS = "the signed webhook allowlist matches the registered webhook routes"

DOC_STATUS_PREFIX = _letters(string.ascii_uppercase, 3, 3)
DOC_STATUS_TYPES = ["SPEC", "PRT", "RPT", "STD"]
DOC_STATUS_PAGE_BODY = {
    "description": "Created as the create page does",
    "content_json": None,
    "status": "Draft",
    "visibility": "internal",
}
DOC_STATUS_DRAFT = "Draft"
DOC_STATUS_PLAIN = {"title": "Specification", "doc_type": "SPEC"}
DOC_STATUS_REFUSED = ["Review", "Approved", "Rejected", "Obsolete"]
DOC_STATUS_REFUSED_TYPE = "SPEC"
DOC_STATUS_FIELD = ["body", "status"]
MSG_DOC_STATUS_CREATED = "the create page's body creates the document"
MSG_DOC_STATUS_TYPE = "the document keeps the kind it was created with"
MSG_DOC_STATUS_DRAFT = "the document starts in Draft"
MSG_DOC_STATUS_REFUSED = "a first status other than Draft is refused with 422"
MSG_DOC_STATUS_FIELD = "the refusal points at the status field"
MSG_DOC_STATUS_LISTED = "the project's documents are listed"
MSG_DOC_STATUS_NOTHING = "a refused create leaves no document"

NGINX_CONF = "docker/nginx.conf"
NGINX_HEADERS_CONF = "docker/security-headers.conf"
NGINX_REQUIRED_HEADERS = (
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Content-Security-Policy",
)
NGINX_ALWAYS = "always;"
NGINX_INCLUDE = "include /etc/nginx/security-headers.conf;"
NGINX_SCRIPT_SRC = "script-src 'self'"
NGINX_UNSAFE_INLINE = "unsafe-inline"
NGINX_FRAME_ANCESTORS = "frame-ancestors 'self'"
NGINX_IMAGE_COPY = "docker/security-headers.conf /etc/nginx/security-headers.conf"
MSG_NGINX_HEADER = "the shared header file sets the header"
MSG_NGINX_ALWAYS = "the header is marked always, so it survives error responses"
MSG_NGINX_SERVER_INCLUDE = "the server block includes the shared header file"
MSG_NGINX_LOCATION_INCLUDE = (
    "a location setting its own header includes the shared header file again"
)
MSG_NGINX_SCRIPT_SRC = "the content security policy allows scripts from the site only"
MSG_NGINX_NO_INLINE = "the content security policy forbids inline script"
MSG_NGINX_FRAMES = "the content security policy allows framing by the site only"
MSG_NGINX_IMAGE = "the image ships the shared header file"

DATABASE_ID_ROUTES = {
    "BLOOM-128": frozenset(
        {
            "DELETE /api/requirements/{requirement_id}",
            "GET /api/requirements/{requirement_id}",
            "PATCH /api/requirements/{requirement_id}",
            "POST /api/requirements/{requirement_id}/link-testrun",
            "GET /api/requirements/{requirement_id}/test-runs",
            "DELETE /api/test-cases/{test_case_id}",
            "GET /api/test-cases/{test_case_id}",
            "PATCH /api/test-cases/{test_case_id}",
        }
    ),
    "BLOOM-129": frozenset(
        {
            "DELETE /api/changes/{change_id}",
            "GET /api/changes/{change_id}",
            "PATCH /api/changes/{change_id}",
            "DELETE /api/defects/{defect_pk}",
            "GET /api/defects/{defect_pk}",
            "PATCH /api/defects/{defect_pk}",
            "POST /api/defects/{defect_pk}/refresh-external",
            "DELETE /api/designs/{design_id}",
            "GET /api/designs/{design_id}",
            "PATCH /api/designs/{design_id}",
            "DELETE /api/document-sections/{section_id}",
            "PATCH /api/document-sections/{section_id}",
            "DELETE /api/documents/{document_id}",
            "GET /api/documents/{document_id}",
            "PATCH /api/documents/{document_id}",
            "POST /api/documents/{document_id}/sections",
            "POST /api/documents/{document_id}/sections/reorder",
            "GET /api/projects/{project_id}/documents",
            "POST /api/projects/{project_id}/documents",
            "DELETE /api/risks/{risk_id}",
            "GET /api/risks/{risk_id}",
            "PATCH /api/risks/{risk_id}",
            "DELETE /api/test-concepts/{concept_id}",
            "GET /api/test-concepts/{concept_id}",
            "PATCH /api/test-concepts/{concept_id}",
        }
    ),
    "BLOOM-130": frozenset(
        {
            "DELETE /api/baselines/{baseline_id}",
            "GET /api/baselines/{baseline_id}",
            "PATCH /api/baselines/{baseline_id}",
            "GET /api/projects/{project_id}/export/requirements",
            "GET /api/projects/{project_id}/export/test-cases",
            "GET /api/projects/{project_id}/export/traceability",
            "GET /api/projects/{project_id}/export/verification-dossier",
            "GET /api/traceability/coverage-gaps/{project_id}",
            "GET /api/traceability/impact/{requirement_id}",
        }
    ),
    "BLOOM-131": frozenset(
        {
            "DELETE /api/attachments/{attachment_id}",
            "GET /api/attachments/{attachment_id}/download",
            "GET /api/documents/{document_id}/attachments",
            "POST /api/documents/{document_id}/attachments",
            "DELETE /api/project-variables/{item_id}",
            "PATCH /api/project-variables/{item_id}",
            "DELETE /api/projects/{project_id}",
            "GET /api/projects/{project_id}",
            "PATCH /api/projects/{project_id}",
            "GET /api/projects/{project_id}/access",
            "GET /api/projects/{project_id}/capabilities",
            "GET /api/projects/{project_id}/members",
            "POST /api/projects/{project_id}/members",
            "DELETE /api/projects/{project_id}/members/{membership_id}",
            "GET /api/projects/{project_id}/members/{membership_id}",
            "PATCH /api/projects/{project_id}/members/{membership_id}",
            "GET /api/projects/{project_id}/permissions",
            "DELETE /api/service-credentials/{credential_id}",
            "POST /api/service-credentials/{credential_id}/rotate",
        }
    ),
    "UNASSIGNED": frozenset(
        {
            "POST /api/access-requests/{request_id}/decision",
            "POST /api/artefact-requests/{request_id}/decline",
            "POST /api/artefacts/{artefact_type}/{artefact_id}/comments/{comment_id}/reopen",
            "POST /api/artefacts/{artefact_type}/{artefact_id}/comments/{comment_id}/resolve",
            "GET /api/artefacts/{artefact_type}/{artefact_id}/tags",
            "PUT /api/artefacts/{artefact_type}/{artefact_id}/tags",
            "GET /api/artefacts/{slug}/{identifier}/revisions/{number}",
            "GET /api/artefacts/{slug}/{identifier}/revisions/{number}/attachments/{file_id}",
            "POST /api/bud/report-requests/{request_id}/refuse",
            "DELETE /api/groups/{group_id}",
            "GET /api/groups/{group_id}",
            "PATCH /api/groups/{group_id}",
            "POST /api/groups/{group_id}/assignments",
            "POST /api/groups/{group_id}/grants",
            "DELETE /api/groups/{group_id}/grants/{grant_id}",
            "PATCH /api/groups/{group_id}/grants/{grant_id}",
            "POST /api/groups/{group_id}/members",
            "DELETE /api/groups/{group_id}/members/{user_id}",
            "DELETE /api/integrations/settings/{setting_id}",
            "PATCH /api/integrations/settings/{setting_id}",
            "POST /api/integrations/settings/{setting_id}/jira/pull",
            "DELETE /api/links/{link_id}",
            "POST /api/notifications/{notification_id}/read",
            "DELETE /api/policies/{policy_id}",
            "GET /api/policies/{policy_id}",
            "PATCH /api/policies/{policy_id}",
            "POST /api/policies/{policy_id}/duplicate",
            "GET /api/projects/{project_id}/artefact-requests",
            "POST /api/projects/{project_id}/import",
            "POST /api/projects/{project_id}/import/markdown",
            "POST /api/projects/{project_id}/import/reqif",
            "POST /api/projects/{project_id}/import/test-cases",
            "POST /api/projects/{project_id}/import/testrail",
            "POST /api/projects/{project_id}/import/testrail/columns",
            "PATCH /api/tags/{tag_id}",
            "DELETE /api/users/{user_id}",
            "GET /api/users/{user_id}",
            "PATCH /api/users/{user_id}",
            "GET /api/users/{user_id}/access-summary",
            "GET /api/users/{user_id}/application-policies",
            "PUT /api/users/{user_id}/application-policies",
            "DELETE /api/users/{user_id}/email",
            "POST /api/users/{user_id}/email",
            "POST /api/users/{user_id}/email/approve",
            "POST /api/users/{user_id}/resend-invite",
            "POST /api/users/{user_id}/revoke-invite",
        }
    ),
}
DATABASE_ID_FREE_PREFIXES = ("/api/test-suites", "/api/campaigns")
MSG_DATABASE_ID_UNLISTED = "no API route outside the allowlist takes a database id in its path"
MSG_DATABASE_ID_STALE = "every allowlisted route still takes a database id in its path"
MSG_DATABASE_ID_ONE_OWNER = "each allowlisted route belongs to one group only"
MSG_DATABASE_ID_SUITES = "suite and campaign routes take no database id"

TAG_PREFIX = "PRJ"
TAG_ADMIN = f"tags-{_letters(string.ascii_lowercase, 4, 8)}@example.com"
TAG_ADMIN_ROLE = "admin"
TAG_REQUIREMENTS = [
    {"req_id": "PRJ-REQ-001", "title": "Source"},
    {"req_id": "PRJ-REQ-002", "title": "Target"},
]
TAG_KIND = "REQ"
TAG_INVALID_PAIRS = [("TC", "REQ"), ("REQ", "UNKNOWN")]
TAG_CREATED = 1
TAG_NONE_CREATED = 0
TAG_LINK = ("REQ", "REQ", "references")
TAG_NO_LINKS = []
MSG_TAG_CREATED = "a tag between two requirements creates one link"
MSG_TAG_LINK = "the tag link is a references link between the two requirements"
MSG_TAG_REPEATED = "syncing the same tag again creates nothing"
MSG_TAG_REFUSED = "a tag pair the rules do not allow is refused with 422"
MSG_TAG_REFUSAL_NAMES = "the refusal names the kind"
MSG_TAG_NO_LINK = "a refused or hidden tag leaves no link"
MSG_TAG_HIDDEN = "a tag the user may not see is skipped without error"
MSG_TAG_SELF = "a body tagging itself creates nothing"

LOGO_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
LOGO_PNG_TYPE = "image/png"
LOGO_FILE = "logo.png"
LOGO_NOT_IMAGE = b"nope"
LOGO_TEXT_TYPE = "text/plain"
LOGO_PREFIX = "PRJ"
LOGO_ADMIN = f"logo-{_letters(string.ascii_lowercase, 4, 8)}@example.com"
LOGO_ADMIN_ROLE = "admin"
LOGO_REQUIREMENT = {"req_id": "PRJ-REQ-001", "title": "Login", "status": "Approved"}
LOGO_REQUIREMENT_KIND = "REQ"
LOGO_PDF_HEADER = b"%PDF-"
STATUS_UNSUPPORTED_MEDIA = 415
MSG_LOGO_TYPE = "the stored logo keeps its image type"
MSG_LOGO_SIZE = "the stored logo keeps its size"
MSG_LOGO_BODY = "the logo is served as uploaded"
MSG_LOGO_MEDIA = "the logo is served with its image type"
MSG_LOGO_REPORT = "reports use the stored logo"
MSG_LOGO_DELETED = "a deleted logo answers 404"
MSG_LOGO_REPORT_NONE = "reports have no logo after it is deleted"
MSG_LOGO_NOT_IMAGE = "a logo that is not an image is refused with 415"
MSG_LOGO_PDF = "the requirements report is a PDF"
MSG_LOGO_PDF_SIZE = "the report with the logo is at least as large as the one without"

PROMOTION_EMAILS = [
    f"user-{_letters(string.ascii_lowercase, 4, 8)}-{n}@example.com" for n in range(4)
]
PROMOTION_ADMIN = "admin"
PROMOTION_MAINTAINER = "maintainer"
PROMOTION_CREATED = [STATUS_OK, STATUS_CREATED]
PROMOTION_ONLY_SEED = "Only the initial administrator can promote users to admin"
PROMOTION_ADMIN_FIXED = "Admin role cannot be changed"
MSG_PROMOTION_SIGN_IN = "the account signs in"
MSG_PROMOTION_CREATED = "the account is created"
MSG_PROMOTION_DONE = "the initial administrator promotes a maintainer"
MSG_PROMOTION_ROLE = "the promoted user is an admin"
MSG_PROMOTION_REFUSED = "another admin may not promote anyone to admin"
MSG_PROMOTION_REFUSAL_TEXT = "the refusal names the initial administrator"
MSG_DEMOTION_REFUSED = "an admin may not be demoted"
MSG_DEMOTION_REFUSAL_TEXT = "the refusal says the admin role is fixed"

TEXT_PREFIX = "PRJ"
TEXT_COPY_PREFIXES = ("ABC", "XYZ")
TEXT_ADMIN = f"text-{_letters(string.ascii_lowercase, 4, 8)}@example.com"
TEXT_ADMIN_ROLE = "admin"
TEXT_BODY = {
    "type": "doc",
    "content": [
        {"type": "heading", "content": [{"type": "text", "text": "Boot"}]},
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Within "},
                {"type": "mention", "attrs": {"label": "BOOT_MS", "mentionSuggestionChar": "{{"}},
                {"type": "text", "text": ", see "},
                {
                    "type": "mention",
                    "attrs": {"label": "PRJ-DES-001", "mentionSuggestionChar": "#"},
                },
                {"type": "text", "text": ", ask "},
                {
                    "type": "mention",
                    "attrs": {"label": "Grace Hopper", "mentionSuggestionChar": "@"},
                },
            ],
        },
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "cold"}]}
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "warm"}]}
                    ],
                },
            ],
        },
    ],
}
TEXT_BODY_PLAIN = "Boot\nWithin {{BOOT_MS}}, see #PRJ-DES-001, ask @Grace Hopper\ncold\nwarm"
TEXT_PLAIN_CASES = [
    ((TEXT_BODY, None), TEXT_BODY_PLAIN),
    ((None, "<p>A &amp; B</p><p>C<br>D</p>"), "A & B\nC\nD"),
    ((None, None), ""),
]
TEXT_DESCRIPTION_CASES = [
    ((None, None, "<p>Boots fast</p>"), "Boots fast"),
    (("Short", None, "<p>Long text</p>"), "Short\n\nLong text"),
    (("Boots fast.", None, "<p>Boots fast</p>"), "Boots fast."),
]
TEXT_COPY_SOURCE = {
    "req_id": "ABC-REQ-001",
    "title": "Boot",
    "description": "Boots fast",
    "content_json": {"type": "doc", "content": []},
    "content_html": "<p>Boots fast</p>",
}
TEXT_COPY_EXPECTED = [("XYZ-REQ-001", "Boot", "Boots fast", None, None)]
TEXT_NO_CONTENT = (None, None)
REQIF_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF xmlns="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <CORE-CONTENT>
    <REQ-IF-CONTENT>
      <DATATYPES>
        <DATATYPE-DEFINITION-ENUMERATION IDENTIFIER="DT-PRIO" LONG-NAME="Priority">
          <SPECIFIED-VALUES>
            <ENUM-VALUE IDENTIFIER="PRIO-HIGH" LONG-NAME="High"/>
            <ENUM-VALUE IDENTIFIER="PRIO-MED" LONG-NAME="Medium"/>
            <ENUM-VALUE IDENTIFIER="PRIO-LOW" LONG-NAME="Low"/>
          </SPECIFIED-VALUES>
        </DATATYPE-DEFINITION-ENUMERATION>
      </DATATYPES>
      <SPEC-TYPES>
        <SPEC-OBJECT-TYPE IDENTIFIER="OT-REQ" LONG-NAME="Requirement Type">
          <SPEC-ATTRIBUTES>
            <ATTRIBUTE-DEFINITION-STRING IDENTIFIER="AD-HEADING" LONG-NAME="ReqIF.ChapterName"/>
            <ATTRIBUTE-DEFINITION-XHTML IDENTIFIER="AD-TEXT" LONG-NAME="ReqIF.Text"/>
            <ATTRIBUTE-DEFINITION-STRING IDENTIFIER="AD-FID" LONG-NAME="ReqIF.ForeignID"/>
            <ATTRIBUTE-DEFINITION-ENUMERATION IDENTIFIER="AD-PRIO" LONG-NAME="Priority">
              <TYPE>
                <DATATYPE-DEFINITION-ENUMERATION-REF>DT-PRIO</DATATYPE-DEFINITION-ENUMERATION-REF>
              </TYPE>
            </ATTRIBUTE-DEFINITION-ENUMERATION>
          </SPEC-ATTRIBUTES>
        </SPEC-OBJECT-TYPE>
        <SPEC-RELATION-TYPE IDENTIFIER="RT-REFINES" LONG-NAME="Refines"/>
      </SPEC-TYPES>
      <SPEC-OBJECTS>
        <SPEC-OBJECT IDENTIFIER="OBJ-1">
          <VALUES>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="System Requirements">
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-STRING-REF>AD-HEADING</ATTRIBUTE-DEFINITION-STRING-REF>
              </DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
          </VALUES>
        </SPEC-OBJECT>
        <SPEC-OBJECT IDENTIFIER="OBJ-2">
          <VALUES>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="Login">
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-STRING-REF>AD-HEADING</ATTRIBUTE-DEFINITION-STRING-REF>
              </DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
            <ATTRIBUTE-VALUE-XHTML>
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-XHTML-REF>AD-TEXT</ATTRIBUTE-DEFINITION-XHTML-REF>
              </DEFINITION>
              <THE-VALUE><xhtml:div>The system <xhtml:b>shall</xhtml:b> allow login.</xhtml:div></THE-VALUE>
            </ATTRIBUTE-VALUE-XHTML>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="PRJ-042">
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-STRING-REF>AD-FID</ATTRIBUTE-DEFINITION-STRING-REF>
              </DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
            <ATTRIBUTE-VALUE-ENUMERATION>
              <DEFINITION>
                <ATTRIBUTE-DEFINITION-ENUMERATION-REF>AD-PRIO</ATTRIBUTE-DEFINITION-ENUMERATION-REF>
              </DEFINITION>
              <VALUES>
                <ENUM-VALUE-REF>PRIO-HIGH</ENUM-VALUE-REF>
              </VALUES>
            </ATTRIBUTE-VALUE-ENUMERATION>
          </VALUES>
        </SPEC-OBJECT>
      </SPEC-OBJECTS>
      <SPEC-RELATIONS>
        <SPEC-RELATION IDENTIFIER="REL-1">
          <TYPE><SPEC-RELATION-TYPE-REF>RT-REFINES</SPEC-RELATION-TYPE-REF></TYPE>
          <SOURCE><SPEC-OBJECT-REF>OBJ-2</SPEC-OBJECT-REF></SOURCE>
          <TARGET><SPEC-OBJECT-REF>OBJ-1</SPEC-OBJECT-REF></TARGET>
        </SPEC-RELATION>
      </SPEC-RELATIONS>
      <SPECIFICATIONS>
        <SPECIFICATION IDENTIFIER="SPEC-1" LONG-NAME="System Specification">
          <CHILDREN>
            <SPEC-HIERARCHY IDENTIFIER="H-1">
              <OBJECT><SPEC-OBJECT-REF>OBJ-1</SPEC-OBJECT-REF></OBJECT>
              <CHILDREN>
                <SPEC-HIERARCHY IDENTIFIER="H-2">
                  <OBJECT><SPEC-OBJECT-REF>OBJ-2</SPEC-OBJECT-REF></OBJECT>
                </SPEC-HIERARCHY>
              </CHILDREN>
            </SPEC-HIERARCHY>
          </CHILDREN>
        </SPECIFICATION>
      </SPECIFICATIONS>
    </REQ-IF-CONTENT>
  </CORE-CONTENT>
</REQ-IF>
""".encode("utf-8")
REQIF_FIELDS = (
    "req_id",
    "title",
    "priority",
    "description",
    "content_json",
    "content_html",
    "req_origin",
    "source_ref",
)
REQIF_COUNTS = (2, 1, 1, ["PRJ-REQ-001", "PRJ-REQ-002"])
REQIF_LOGIN = (
    "PRJ-REQ-002",
    "Login",
    "High",
    "The system shall allow login.",
    None,
    None,
    "External",
    "OBJ-2",
)
REQIF_SYSTEM_SOURCE = ("PRJ-REQ-001", "System Requirements", "OBJ-1")
REQIF_LINK = ("REQ", "REQ", "refines")
REQIF_NO_REQUIREMENT_LINKS = 0
MSG_TEXT_PLAIN = "editor content becomes plain lines with mentions as @Name, #ID and {{KEY}}"
MSG_TEXT_DESCRIPTION = "the text fills or follows a description that does not already hold it"
MSG_TEXT_COPY = "a copied requirement keeps its description and no editor content"
MSG_REQIF_COUNTS = "the ReqIF import creates two requirements, one link and one specification"
MSG_REQIF_LOGIN = "an imported requirement holds its ReqIF text as plain description"
MSG_REQIF_SYSTEM = "the heading object is imported with its title and source"
MSG_REQIF_LINK = "the ReqIF relation becomes one refines link from login to system"
MSG_REQIF_LEGACY = "the import writes no legacy requirement links"

DESCRIPTION_PREFIX = _letters(string.ascii_uppercase, 3, 3)
DESCRIPTION_BODY = {
    "type": "doc",
    "content": [
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "boots in "},
                {
                    "type": "mention",
                    "attrs": {"id": "1", "label": "BOOT_BUDGET_MS", "mentionSuggestionChar": "{{"},
                },
            ],
        }
    ],
}
DESCRIPTION_BODY_HTML = "<p>boots in {{BOOT_BUDGET_MS}}</p>"
DESCRIPTION_FROM_BODY = ("boots in {{BOOT_BUDGET_MS}}", None, None)
DESCRIPTION_EDIT_HTML = "<p>and logs <b>every</b> boot</p>"
DESCRIPTION_AFTER_EDIT = ("boots in {{BOOT_BUDGET_MS}}\n\nand logs every boot", None, None)
DESCRIPTION_SPEC_TITLE = "Target specification"
DESCRIPTION_UNKNOWN_TAG = "#XYZ-SPEC-999"
DESCRIPTION_UNTAGGED = "No tag yet."
DESCRIPTION_TAG_TYPE = "SPEC"
DESCRIPTION_TAG_ROLE = "references"
MSG_DESCRIPTION_CREATED = "a requirement is created"
MSG_DESCRIPTION_FROM_BODY = (
    "editor content sent on create becomes the description and is not stored"
)
MSG_DESCRIPTION_DETAIL = "the requirement detail holds the description and no editor content"
MSG_DESCRIPTION_EDIT = "editor content sent on edit follows the description and is not stored"
MSG_DESCRIPTION_TAG_CREATE = (
    "a #ID in a new description links the requirement to that document only"
)
MSG_DESCRIPTION_NO_TAG = "a description without a tag creates no link"
MSG_DESCRIPTION_TAG_EDIT = "a #ID added on edit links the requirement to that document"

TEXT_MIGRATION_BEFORE = "a7d2c5f81b39"
TEXT_MIGRATION_REVISION = "b8e3d1f6a920"
TEXT_MIGRATION_PREFIX = "PRJ"
TEXT_MIGRATION_ROWS = [
    ("PRJ-REQ-001", None, TEXT_BODY, None),
    ("PRJ-REQ-002", "Short", None, "<p>Long text</p>"),
    ("PRJ-REQ-003", "Boots fast.", None, "<p>Boots fast</p>"),
    ("PRJ-REQ-004", "Plain only", None, None),
]
TEXT_MIGRATION_EXPECTED = {
    "PRJ-REQ-001": (TEXT_BODY_PLAIN, None, None),
    "PRJ-REQ-002": ("Short\n\nLong text", None, None),
    "PRJ-REQ-003": ("Boots fast.", None, None),
    "PRJ-REQ-004": ("Plain only", None, None),
}
MSG_TEXT_MIGRATION_UPGRADE = "the upgrade moves each requirement's editor text into its description"
MSG_TEXT_MIGRATION_DOWNGRADE = "the downgrade keeps the descriptions and restores no editor content"
MSG_TEXT_MIGRATION_REUPGRADE = "upgrading again leaves the descriptions as they are"
SERVICE_ADMIN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
SERVICE_NAME = "Bud"
SERVICE_TOKEN_PREFIX = "blm_sync_"
SERVICE_SCOPE = "test-results:write"
SERVICE_LIFETIME = timedelta(days=90, seconds=5)
SERVICE_REFUSED = (None, 401)
MSG_SERVICE_PREFIX = "a service token starts with blm_sync_"
MSG_SERVICE_SCOPE = "a service credential is scoped to writing test results"
MSG_SERVICE_HASH = "the stored hash does not contain the token"
MSG_SERVICE_LIFETIME = "a service credential expires within 90 days"
MSG_SERVICE_AUTHENTICATES = "the token authenticates as the credential it was issued for"
MSG_SERVICE_NOT_A_USER = "a service token is refused as a user sign-in with 401"
MSG_SERVICE_UNTYPED = "a user token without a type is refused with 401"
MSG_SERVICE_REVOKED = "the token of a revoked credential is refused with 401"
MSG_SERVICE_EXPIRED = "the token of an expired credential is refused with 401"
SECRETS_TOKEN = f"ghp_{_letters(string.ascii_letters + string.digits, 24, 32)}"
SECRETS_WEBHOOK = _letters(string.ascii_letters + string.digits, 24, 32)
SECRETS_ROTATED = f"ghp_{_letters(string.ascii_letters + string.digits, 24, 32)}"
SECRETS_PLAINTEXT = _letters(string.ascii_letters, 16, 24)
SECRETS_MALFORMED_KEY = "not-a-valid-fernet-key"
SECRETS_TRACKER = "github"
SECRETS_UNAVAILABLE = 503
MSG_SECRETS_PREFIX = "an encrypted secret starts with the envelope prefix"
MSG_SECRETS_HIDDEN = "the envelope does not contain the secret"
MSG_SECRETS_ROUND_TRIP = "the envelope decrypts to the secret"
MSG_SECRETS_DISTINCT = "the same secret encrypts to a different envelope each time"
MSG_SECRETS_BOTH_DECRYPT = "both envelopes decrypt to the secret"
MSG_SECRETS_NO_KEY = "without a key encrypting is refused with 503"
MSG_SECRETS_BAD_KEY = "with a malformed key encrypting is refused with 503"
MSG_SECRETS_WRONG_KEY = "with another key decrypting is refused with 503"
MSG_SECRETS_PLAINTEXT = "a stored value that is not an envelope is refused with 503"
MSG_SECRETS_RECOGNISED = "an envelope counts as encrypted, plaintext and nothing do not"
MSG_SECRETS_CREATED = "the setting is created with 201"
MSG_SECRETS_REPORTED = "the answer says a token and a webhook secret are set"
MSG_SECRETS_NOT_SHOWN = "the answer does not contain the {secret}"
MSG_SECRETS_STORED = "the token and the webhook secret are stored as envelopes"
MSG_SECRETS_STORED_VALUES = "the stored envelopes decrypt to the token and the webhook secret sent"
MSG_SECRETS_ROTATED = "sending a new token is answered 200"
MSG_SECRETS_NEW_ENVELOPE = "the rotation stores another envelope"
MSG_SECRETS_NEW_VALUE = "the stored envelope decrypts to the new token"
HOOK_GITHUB_PATH = "/api/integrations/github/webhook"
HOOK_GITLAB_PATH = "/api/integrations/gitlab/webhook"
HOOK_GITHUB_NUMBER = _draw.randrange(50_000, 60_000)
HOOK_GITLAB_NUMBER = _draw.randrange(60_000, 70_000)
HOOK_WRONG_SIGNATURE = "sha256=" + "0" * 64
HOOK_OVERSIZED_BYTES = 1024 * 1024 + 1
HOOK_DELIVERY = f"delivery-{_letters(string.ascii_lowercase, 6, 10)}"
HOOK_OVERSIZED_DELIVERY = f"delivery-{_letters(string.ascii_lowercase, 6, 10)}"
HOOK_GITLAB_DELIVERY = f"delivery-{_letters(string.ascii_lowercase, 6, 10)}"
HOOK_PROCESSED = "processed"
HOOK_DUPLICATE = "duplicate"
HOOK_STATUS_KEY = "status"
MSG_HOOK_UNSIGNED = "a GitHub delivery without a signature is refused with 403"
MSG_HOOK_WRONG = "a GitHub delivery with a wrong signature is refused with 403"
MSG_HOOK_NO_DELIVERY = "a signed GitHub delivery without a delivery id is refused with 400"
MSG_HOOK_OVERSIZED = "a signed GitHub delivery over 1 MiB is refused with 413"
MSG_HOOK_UNCHANGED = "after the refused deliveries the defect is still open"
MSG_HOOK_NO_EVENT = "the refused deliveries record no successful sync"
MSG_HOOK_PROCESSED = "a signed GitHub delivery with a delivery id is processed with 200"
MSG_HOOK_CLOSED = "the processed delivery closes the linked defect"
MSG_HOOK_REPLAY = "the same delivery a second time is answered as a duplicate"
MSG_HOOK_GITLAB_UNSIGNED = "a GitLab delivery without the token is refused with 403"
MSG_HOOK_GITLAB_UNCHANGED = "after the refused GitLab delivery the defect is still open"
MSG_HOOK_GITLAB_PROCESSED = "a GitLab delivery with the token is processed with 200"
READER_BASELINE_ID = f"{VISIBILITY_PREFIX}-BL-001"
READER_SNAPSHOT = {
    "requirements": {
        "count": 2,
        "ids": [f"{VISIBILITY_PREFIX}-REQ-001", f"{VISIBILITY_PREFIX}-REQ-002"],
    },
    "test_cases": {
        "count": 2,
        "ids": [f"{VISIBILITY_PREFIX}-TC-001", f"{VISIBILITY_PREFIX}-TC-002"],
    },
}
READER_CUSTOMER_REQ = f"{VISIBILITY_PREFIX}-REQ-001"
READER_INTERNAL_REQ = f"{VISIBILITY_PREFIX}-REQ-002"
READER_REQUIREMENT_KIND = "requirement"
READER_TRACKER = "github"
READER_SECRET_FIELD = "webhook_secret"
READER_VARIABLE_KEY = "API_KEY"
READER_VARIABLE_VALUE = _letters(string.ascii_letters + string.digits, 16, 24)
READER_MAINTAINER_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
READER_ALL_PERMISSIONS = {"*": ["*"]}
MSG_READER_BASELINE = "an external reader's read of a baseline is answered 200"
MSG_READER_NO_SNAPSHOT = "the baseline an external reader gets has no snapshot"
MSG_READER_SETTINGS = (
    "an external reader's list of the tracker settings is answered 200 with the one setting"
)
MSG_READER_SETTING_FLAGS = "the setting says a token and a webhook secret are set"
MSG_READER_NO_SECRET = "the setting does not contain the webhook secret"
MSG_READER_RELATED_HIDDEN = (
    "the related artefacts of an internal requirement are answered 404 to an external reader"
)
MSG_READER_RELATED_SHOWN = (
    "the related artefacts of a customer requirement are answered 200 to an external reader"
)
MSG_READER_VARIABLES_REFUSED = (
    "an external reader's list of the project parameters is refused with 403"
)
MSG_READER_VARIABLES_SHOWN = "a member with every permission lists the project parameter"
READER_CUSTOMER_TC = f"{VISIBILITY_PREFIX}-TC-001"
READER_INTERNAL_TC = f"{VISIBILITY_PREFIX}-TC-002"
READER_VISIBLE_COMMENT = " ".join(_draw.sample(_WORDS, 3))
READER_HIDDEN_COMMENT = " ".join(_draw.sample(_WORDS, 3))
READER_VISIBLE_ACTIVITY = " ".join(_draw.sample(_WORDS, 3))
READER_HIDDEN_ACTIVITY = " ".join(_draw.sample(_WORDS, 3))
READER_LINK = ("TC", "REQ", "verifies")
MSG_READER_TC_LIST = "an external reader lists the customer test case and not the internal one"
MSG_READER_TC_VISIBILITY = "a test case read by an administrator carries its visibility"
MSG_READER_COMMENTS_HIDDEN = (
    "the comments of an internal requirement are answered 404 to an external reader"
)
MSG_READER_ACTIVITY_HIDDEN = (
    "the activity of an internal requirement is answered 404 to an external reader"
)
MSG_READER_COMMENTS_SHOWN = "an external reader gets the comment of the customer requirement"
MSG_READER_ACTIVITY_SHOWN = "an external reader gets the activity of the customer requirement"
MSG_READER_LINKS = "an external reader lists only the link whose two ends are customer artefacts"
IAMHTTP_ALLOWED_PREFIX = "ABC"
IAMHTTP_BLOCKED_PREFIX = "PRJ"
IAMHTTP_BLOCKED_REQ = "PRJ-REQ-001"
IAMHTTP_MAINTAINER_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
IAMHTTP_REQIF = b"<REQ-IF/>"
IAMHTTP_DOC_TYPE = "REQ"
MSG_IAMHTTP_PROJECTS = "a member of one project lists that project only"
MSG_IAMHTTP_LIST = "the requirements of a project the member is not in are refused with 403"
MSG_IAMHTTP_READ = "a requirement of a project the member is not in is answered 404"
MSG_IAMHTTP_TRACEABILITY = "the traceability of a project the member is not in is refused with 403"
MSG_IAMHTTP_DASHBOARD = "the dashboard shows the member's project only"
MSG_IAMHTTP_IMPORT = "importing from a project the member is not in is refused with 403"
MSG_IAMHTTP_REQIF = "an external reader's ReqIF upload is refused with 403"
EXPORT_ADMIN_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EXPORT_READER_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EXPORT_AUTHOR_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
EXPORT_PREFIX = "PRJ"
EXPORT_SHOWN_REQ = "PRJ-REQ-001"
EXPORT_HIDDEN_REQ = "PRJ-REQ-002"
EXPORT_SHOWN_TC = "PRJ-TC-001"
EXPORT_HIDDEN_TC = "PRJ-TC-002"
EXPORT_SHOWN_TITLE = "Shown"
EXPORT_HIDDEN_TITLE = "Hidden"
EXPORT_PASSED = "Passed"
EXPORT_PDF_KINDS = ("requirements", "traceability", "test-cases", "verification-dossier")
EXPORT_DOSSIER = "verification-dossier"
EXPORT_AUDIT_ACTION = "export.generated"
EXPORT_AUDIT_KINDS = ["requirements", "test_cases", "traceability", "verification_dossier"]
EXPORT_PDF = (200, "application/pdf", True)
EXPORT_READER_PERMISSIONS = {"REQ": ["view", "export"], "TC": ["view", "export"]}
EXPORT_AUTHOR_PERMISSIONS = {"REQ": ["view", "export"]}
MSG_EXPORT_PDF = "the {kind} export is answered 200 as a PDF"
MSG_EXPORT_AUDITED = "each of the four PDF exports is recorded with its kind"
MSG_EXPORT_REQUIREMENTS = (
    "an external exporter's requirements export holds the customer requirement only"
)
MSG_EXPORT_MATRIX = "an external exporter's traceability export holds the customer pair only"
MSG_EXPORT_TESTS = "an external exporter's test case export holds the customer test case only"
MSG_EXPORT_NO_HIDDEN = "the {kind} export does not contain the internal title"
MSG_EXPORT_DOSSIER = "the dossier is refused with 403 to an exporter of requirements only"
READER_CUSTOMER_SPEC = f"{VISIBILITY_PREFIX}-SPEC-001"
READER_INTERNAL_SPEC = f"{VISIBILITY_PREFIX}-SPEC-002"
READER_DOC_TYPES = ["REQ", "SPEC"]
READER_REQUIREMENTS_SLUG = "requirements"
READER_SPECIFICATIONS_SLUG = "specifications"
READER_DETAIL_STATUSES = (200, 404, 200, 404)
READER_CUSTOMER_ORIGIN = "Customer"
READER_INTERNAL_ORIGIN = "Internal"
READER_NEW_TITLE = " ".join(_draw.sample(_WORDS, 3))
MSG_READER_DOCS_LIST = (
    "an external reader lists the customer requirement and the customer specification only"
)
MSG_READER_DOCS_VISIBILITY = "every listed document carries the customer visibility"
MSG_READER_DOCS_DETAIL = (
    "the customer documents open with 200 and the internal ones are answered 404"
)
MSG_READER_REQ_LIST = "an external reader lists the customer requirement and not the internal one"
MSG_READER_REQ_HIDDEN = "an internal requirement is answered 404 to an external reader"
MSG_READER_ORIGIN_CUSTOMER = "a requirement created with the Customer origin is customer-visible"
MSG_READER_ORIGIN_INTERNAL = "a requirement changed to the Internal origin becomes internal"
READER_COVERAGE = (1, 1, 0)
MSG_READER_MATRIX = "an external reader's traceability holds the customer requirement with the customer test case only"
MSG_READER_COVERAGE = (
    "an external reader's coverage counts the customer requirement only, as covered"
)
MSG_READER_IMPACT_HIDDEN = (
    "the impact of an internal requirement is answered 404 to an external reader"
)
READER_VISIBLE_SUITE = f"{VISIBILITY_PREFIX}-TS-001"
READER_HIDDEN_SUITE = f"{VISIBILITY_PREFIX}-TS-002"
READER_EXECUTED_AT = datetime(2026, 7, 2, 10, 30, 0)
READER_EXECUTED_AT_TEXT = "2026-07-02T10:30:00"
READER_BUD_RUN = _draw.randrange(100, 10_000)
READER_SUITE_EXECUTION = (1, "Passed", READER_EXECUTED_AT_TEXT, READER_BUD_RUN)
MSG_READER_SUITE_LIST = "an external reader lists the customer suite and not the internal one"
MSG_READER_SUITE_LIST_EXECUTION = (
    "the listed suite counts its one visible test case and carries its last execution"
)
MSG_READER_SUITE_HIDDEN = "an internal suite is answered 404 to an external reader"
MSG_READER_SUITE_SHOWN = "the customer suite opens with 200 and carries its visibility"
MSG_READER_SUITE_EXECUTION = (
    "the opened suite counts its one visible test case and carries its last execution"
)
MSG_READER_SUITE_ITEMS = "the opened suite holds the customer test case and not the internal one"
CONTROLLED_KINDS = [
    ("design", "/api/designs", "design_id", "DES"),
    ("risk", "/api/risks", "risk_id", "RSK"),
    ("change", "/api/changes", "change_id", "CHG"),
    ("concept", "/api/test-concepts", "concept_id", "CPT"),
    ("defect", "/api/defects", "defect_id", "DEF"),
]
MSG_CONTROLLED_LIST = "an external reader lists the customer {kind} and not the internal one"
MSG_CONTROLLED_HIDDEN = "an internal {kind} is answered 404 to an external reader"
MSG_CONTROLLED_SHOWN = "the customer {kind} opens with 200 and carries its id and visibility"
READER_VISIBLE_CAMPAIGN = f"{VISIBILITY_PREFIX}-CMP-001"
READER_HIDDEN_CAMPAIGN = f"{VISIBILITY_PREFIX}-CMP-002"
READER_CAMPAIGN_EXECUTED_AT = datetime(2026, 7, 2, 11, 15, 0)
READER_CAMPAIGN_EXECUTION = (1, "Passed", "2026-07-02T11:15:00")
READER_CAMPAIGN_EXECUTED = {"status": "Executed", "result": "Passed"}
READER_CAMPAIGN_PENDING = {"status": "Pending"}
READER_SYNC_AT = "2026-07-04T10:45:00"
READER_SYNC_RUN = _draw.randrange(100, 10_000)
READER_SYNC_COMMENT = " ".join(_draw.sample(_WORDS, 3))
MSG_READER_CAMPAIGN_LIST = "an external reader lists the customer campaign and not the internal one"
MSG_READER_CAMPAIGN_LIST_EXECUTION = (
    "the listed campaign counts its one visible test case and carries its last execution"
)
MSG_READER_CAMPAIGN_HIDDEN = "an internal campaign is answered 404 to an external reader"
MSG_READER_CAMPAIGN_SHOWN = "the customer campaign opens with 200 and carries its visibility"
MSG_READER_CAMPAIGN_EXECUTION = (
    "the opened campaign counts its one visible test case and carries its last execution"
)
MSG_READER_CAMPAIGN_ITEMS = (
    "the opened campaign holds the customer test case and not the internal one"
)
MSG_READER_CAMPAIGN_SUITES = "the opened campaign names the customer suite and not the internal one"
MSG_READER_SYNC = "synchronising a result is answered 200"
MSG_READER_SYNC_NO_RUN = "the synchronised result gives the campaign no Bud run of its own"
MSG_READER_SYNC_ITEM = "the campaign's item carries the synchronised result and its time"
MSG_DIRECT_REQUIREMENT = (
    "the customer requirement shows its customer test case, suite and campaign only"
)
MSG_DIRECT_TEST_CASE = (
    "the customer test case shows its customer requirement, suite and campaign only"
)
MSG_DIRECT_CAMPAIGN = "the customer campaign shows its customer test case and that test case's customer requirement only"
ARQ_BOSS_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
ARQ_SECOND_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
ARQ_MEMBER_EMAIL = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
ARQ_KIND = "requirement"
ARQ_PREFIX = "PRJ"
ARQ_REF = "PRJ-REQ-001"
ARQ_MINE_REF = "PRJ-REQ-002"
ARQ_FAILED_MAIL_REF = "PRJ-REQ-003"
ARQ_DECIDED_PREFIX = "XYZ"
ARQ_DECIDED_REF = "XYZ-REQ-001"
ARQ_OTHER_PREFIX = "ABC"
ARQ_REFUSED_REF = "ABC-REQ-001"
ARQ_PENDING_REF = "ABC-REQ-002"
ARQ_INVALID_REF = "../../etc"
ARQ_ADMIN_REF = "PRJ-REQ-009"
ARQ_MAIL_ERROR = "SMTP is disabled"
ARQ_PENDING = "pending"
ARQ_GRANTED = "granted"
ARQ_REFUSED = "refused"
ARQ_RESOURCE_LABEL = "PRJ-REQ-001 (not found)"
ARQ_REVIEW_LINK_END = "/projects/PRJ/edit"
ARQ_REQUESTED_ACTION = "access.requested"
ARQ_GRANTED_ACTION = "access.granted"
ARQ_REFUSED_ACTION = "access.refused"
ARQ_NOTHING_PHRASE = "nothing to request"
ARQ_FIELDS = [
    "already_requested",
    "created_at",
    "decided_at",
    "id",
    "mail_sent",
    "project_prefix",
    "requester_email",
    "requester_name",
    "requester_profile_picture_url",
    "resource_label",
    "resource_ref",
    "resource_type",
    "status",
]
MSG_ARQ_CREATED = "a first request is created with 201, pending, and reports its mail as sent"
MSG_ARQ_REPEATED = "the same request again is answered 200 as already requested, with the same id"
MSG_ARQ_MAILED = "the request mails each administrator once"
MSG_ARQ_MAIL = (
    "the mail names the requester, the resource, the project, the review page and the request id"
)
MSG_ARQ_RECORDED = "the request is recorded once with its resource"
MSG_ARQ_FIELDS = "the answer holds the request's own fields only"
MSG_ARQ_UNDISCLOSED = "the answer names no requester email and no picture"
MSG_ARQ_NONE_YET = "before a request the page learns that none is pending"
MSG_ARQ_MINE = "after the request the page learns that it is pending"
MSG_ARQ_MAIL_FAILED = (
    "a request whose mail fails is created with 201 and reports its mail as not sent"
)
MSG_ARQ_LISTED = "an administrator lists the request of the project with its requester"
MSG_ARQ_MEMBER_DECISION = "a member's decision is refused with 403"
MSG_ARQ_GRANT = "an administrator's grant is answered 200 as granted"
MSG_ARQ_DECIDED_TWICE = "a second decision on a decided request is refused with 409"
MSG_ARQ_GRANT_RECORDED = "the grant is recorded once with the administrator and the requester"
MSG_ARQ_MEMBER_LIST = "a member's list of every request is refused with 403"
MSG_ARQ_ALL = "an administrator lists every pending request"
MSG_ARQ_REFUSE = "an administrator's refusal is answered 200 as refused"
MSG_ARQ_PENDING_LEFT = "the refused request leaves the pending list"
MSG_ARQ_HISTORY = "the refused request is listed under refused"
MSG_ARQ_REFUSAL_RECORDED = "the refusal is recorded once with the administrator and the requester"
MSG_ARQ_ANONYMOUS = "a request without a sign-in is refused with 401"
MSG_ARQ_INVALID = "a resource reference with path characters is refused with 422"
MSG_ARQ_ADMIN = "an administrator's own request is refused with 409 as nothing to request"
MSG_ARQ_ADMIN_SILENT = "the administrator's refused request mails nobody and is not recorded"
AUDITLOG_USER_AGENT = "audit-test/1.0"
AUDITLOG_SOMEONE = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
AUDITLOG_MEMBER = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
AUDITLOG_DEMOTED = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
AUDITLOG_ADMIN = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
AUDITLOG_ADMIN_NAME = "Admin"
AUDITLOG_ADA = ("Ada@example.com", "Ada")
AUDITLOG_ZOE = ("Zoe@example.com", "Zoe")
AUDITLOG_PREFIX = "PRJ"
AUDITLOG_DESIGN = "PRJ-DES-001"
AUDITLOG_POLICY = f"Policy {_letters(string.ascii_lowercase, 4, 10)}"
AUDITLOG_SECRET = _letters(string.ascii_letters + string.digits, 24, 32)
AUDITLOG_LOGIN = "auth.login"
AUDITLOG_AUTH_FILTER = "auth."
AUDITLOG_SORT_FILTER = "sort."
AUDITLOG_FAILED_LOGIN = ("failure", "anonymous", "user")
AUDITLOG_ROLE_CHANGE = {"from": "maintainer", "to": "external"}
AUDITLOG_SORT_HOURS = (3, 1, 4, 2)
AUDITLOG_SORT_ROWS = [
    ("zoe", "sort.b", "user", "success", "10.0.0.2", "req-d"),
    ("ada", "sort.d", "project", "failure", None, "req-c"),
    (None, "sort.a", "policy", "ignored", "10.0.0.3", None),
    (999, "sort.c", None, "success", "10.0.0.1", "req-a"),
]
AUDITLOG_SORTED = {
    "occurred_at": ([1, 2, 3, 4], [4, 3, 2, 1]),
    "actor": ([1, 2, 3, 4], [4, 3, 2, 1]),
    "action": ([4, 3, 2, 1], [1, 2, 3, 4]),
    "target": ([2, 4, 1, 3], [3, 1, 4, 2]),
    "outcome": ([1, 4, 3, 2], [2, 3, 4, 1]),
    "ip": ([1, 2, 3, 4], [4, 3, 2, 1]),
    "request_id": ([4, 2, 1, 3], [3, 1, 2, 4]),
}
AUDITLOG_DIRECTIONS = ("asc", "desc")
AUDITLOG_PAGE = 2
AUDITLOG_INVALID = [{"sort": "details"}, {"dir": "sideways"}]
AUDITLOG_MODULE = "app.api.audit"
MSG_AUDITLOG_REFUSED_LOGIN = "a sign-in with a wrong password is refused with 401"
MSG_AUDITLOG_FAILURE = (
    "the refused sign-in is recorded as a failure by an anonymous actor on the account"
)
MSG_AUDITLOG_REQUEST = "the record carries the request id, the user agent and an address"
MSG_AUDITLOG_NO_PASSWORD = "the record does not contain the password that was tried"
MSG_AUDITLOG_SUCCESS = "a sign-in is recorded as a success by that user"
MSG_AUDITLOG_ROLE = (
    "a role change is answered 200 and recorded with the administrator, the account and both roles"
)
MSG_AUDITLOG_STATUSES = (
    "adding a member, changing a visibility and deleting an artefact are answered 201, 200 and 204"
)
MSG_AUDITLOG_MEMBER = "the added member is recorded with the project and the account"
MSG_AUDITLOG_VISIBILITY = (
    "the visibility change is recorded with the artefact and the new visibility"
)
MSG_AUDITLOG_DELETED = "the deletion is recorded with the project and the artefact type"
MSG_AUDITLOG_ROTATED = "a new token is answered 200 and recorded as a changed token field"
MSG_AUDITLOG_NO_SECRET = "the record does not contain the new token"
MSG_AUDITLOG_MEMBER_REFUSED = "a member's read of the audit log is refused with 403"
MSG_AUDITLOG_FILTERED = (
    "an administrator reads the sign-in records, every one of them and nothing else"
)
MSG_AUDITLOG_NEWEST = "the newest record names the administrator who signed in last"
MSG_AUDITLOG_SORT = "sorted by {field} {direction}, two pages of two hold the four records in order"
MSG_AUDITLOG_INVALID = "the query {query} is refused with 422"
MSG_AUDITLOG_READ_ONLY = "every audit endpoint is a GET"
RQA_ADMIN = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
RQA_MEMBER = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
RQA_FORMER = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
RQA_OWNER = f"{_letters(string.ascii_lowercase, 5, 8)}@example.com"
RQA_PREFIX = _letters(string.ascii_uppercase, 3, 3)
RQA_DESIGN = f"{RQA_PREFIX}-DES-001"
RQA_ACTION = "api.request"
RQA_AGENT = "audit-test/1.0"
RQA_TITLE = " ".join(_draw.sample(_WORDS, 2))
RQA_NEW_TITLE = " ".join(_draw.sample(_WORDS, 2))
RQA_LONG_DESCRIPTION = "x" * 2000
RQA_CLIENTS = {"web": "198.51.100.11", "cli": "198.51.100.12"}
RQA_SERVICE_ADDRESS = "198.51.100.13"
RQA_REFUSED_ADDRESS = "198.51.100.14"
RQA_LIMITED_ADDRESS = "198.51.100.15"
RQA_REPEATED_ADDRESS = "198.51.100.16"
RQA_WINDOW_ADDRESS = "198.51.100.17"
RQA_SECRET_ADDRESS = "198.51.100.18"
RQA_FILTER_ADDRESS = "198.51.100.19"
RQA_UNKNOWN_ADDRESS = "203.0.113.9"
RQA_FORGED = {"Authorization": "Bearer forged.token.value"}
RQA_MISSING_ID = 999999
RQA_SERVICE_NAME = "Bud sync"
RQA_RUN = {"bud_run_id": 7, "run_name": "Nightly"}
RQA_LOGIN_LIMIT = 10
RQA_WRONG_LOGIN = {"email": "nobody@example.com", "password": "Wrong-1234"}
RQA_WINDOW_THRESHOLD = 3
RQA_OLD_REFUSALS = 5
RQA_OLD_MINUTES = 11
RQA_WRONG_PASSWORD = "Not-The-Password-9"
RQA_SEARCH = "confidential-search-text"
RQA_EXPLODING_PATH = "/api/__audit_boom__"
RQA_EXPLOSION = "audit boom"
RQA_SUPPLIED_ID = "report-me-500"
RQA_QUOTE = "Quote reference report-me-500 when reporting this."
RQA_FOREIGN_ORIGIN = "https://foreign.example.com"
RQA_FAILURE_LOG = "api.request could not be recorded"
RQA_ROUTE_PATH = "/api/projects/3/things/9"
RQA_ROUTE_TEMPLATE = "/api/projects/{project_id}/things/{thing_id}"
RQA_OUTCOME_CODES = (200, 302, 401, 403, 404, 429, 500)
RQA_OUTCOMES = ["success", "success", "denied", "denied", "failure", "denied", "failure"]
RQA_CREATED_BODIES = ({"id": 4, "doc_id": "PRJ-DOC-004"}, {"id": 5}, None, None)
MSG_RQA_STATUSES = "the {client} read, create, change and delete are answered 200, 201, 200 and 204"
MSG_RQA_GZIP = "the created requirement is answered compressed"
MSG_RQA_ONE_EVENT = "the {what} leaves exactly one api.request record"
MSG_RQA_CALL = "the {client} {method} is recorded with its actor, client, route, status and target"
MSG_RQA_CREATED = "the {client} creation is recorded with the new id and requirement id"
MSG_RQA_PROJECT = "the {client} project read is recorded with the project"
MSG_RQA_SERVICE_STATUSES = (
    "the service credential is issued with 201, and its read and publish are answered 200 and 201"
)
MSG_RQA_SERVICE = "the service {what} is recorded as the credential, with no user and no client"
MSG_RQA_SERVICE_QUERY = "the service read is recorded with its query parameter names"
MSG_RQA_SERVICE_CREATED = "the publish is recorded with the new document id and document number"
MSG_RQA_ISSUED = "the credential issue is recorded with the credential id and without the token"
MSG_RQA_REFUSED_STATUSES = "a forged token, a foreign project, a hidden design and a missing design are answered 401, 403, 404 and 404"
MSG_RQA_DENIED = "the {what} is recorded as denied with the address"
MSG_RQA_REFUSAL_DETAILS = "the forged token is anonymous, the foreign project names the project, the hidden design names the design"
MSG_RQA_MISSING = "the missing design is recorded as a failure"
MSG_RQA_LIMITED = "the first wrong sign-in is answered 401 and the eleventh 429"
MSG_RQA_LIMITED_DENIED = (
    "the refused and the rate-limited sign-in are recorded as denied with the address"
)
MSG_RQA_BELOW = "refusals below the threshold leave no repeated refusal record"
MSG_RQA_DETECTED = "the threshold reached leaves one repeated refusal record with the address, the count and the window"
MSG_RQA_DENIED_COUNT = "every refused request of the address is recorded as denied"
MSG_RQA_OLD = "refusals older than the window do not count"
MSG_RQA_WINDOW = "refusals inside the window reach the threshold once"
MSG_RQA_QUERY_NAMES = "a search is answered 200 and recorded with its parameter name only"
MSG_RQA_NO_SECRET = "no record holds the {secret}"
MSG_RQA_PROBE = (
    "the {route} probe is recorded as anonymous, without credentials, with its status and duration"
)
MSG_RQA_WRITE_FAILED = "a request whose record cannot be written is answered 200 with a request id"
MSG_RQA_NOT_WRITTEN = "no api.request record is written and the failure is logged"
MSG_RQA_FILTER = "the audit log filtered by {field} holds only matching records"
MSG_RQA_FILTER_NONE = "the audit log filtered by an unknown address is empty"
MSG_RQA_TEMPLATE = (
    "a route is recorded as its template with the prefix, an unknown path as unmatched"
)
MSG_RQA_OUTCOMES = "each status maps to its outcome, and a refused 404 is denied"
MSG_RQA_BODIES = (
    "a created body is read plain or compressed, and an oversized or broken one is ignored"
)
MSG_RQA_DEPENDENCY_ACTOR = "the user a dependency signs in is the actor of the record"
MSG_RQA_PREFLIGHT = (
    "an allowed preflight is answered 200 by the CORS layer, with no request id and no record"
)
MSG_RQA_REFUSED_PREFLIGHT = (
    "a preflight from a foreign origin is refused with 403 and recorded as denied"
)
MSG_RQA_FOREIGN = (
    "a request from a foreign origin gets no CORS permission and is recorded as denied"
)
MSG_RQA_CORS_ID = (
    "an allowed origin gets its CORS header and a request id, and the request is recorded"
)
MSG_RQA_500 = (
    "an unhandled error is answered 500 and recorded once as a failure without the error text"
)
MSG_RQA_500_ID = "a 500 quotes the supplied request id in its header, body and record"
MSG_RQA_DEACTIVATED = "a deactivated account is refused with 403 and recorded as that user, denied"
MSG_RQA_NOTIFICATION = "another user's notification and a missing one are both answered 404"
MSG_RQA_NOTIFICATION_OUTCOMES = (
    "another user's notification is recorded as denied and a missing one as a failure"
)
MSG_RQA_404_STATUSES = "a scan, an unknown route and a missing row are answered 404"
MSG_RQA_404 = "the anonymous scan and the unknown route are denied, the missing row of a signed-in user is a failure"
TPX_NETWORK = "10.0.0.0/8"
TPX_FORGED = "198.51.100.9"
TPX_OUTSIDER = "192.0.2.50"
TPX_POSING_HOP = "10.0.0.3"
TPX_FORGED_TOKEN = {"Authorization": "Bearer forged"}
TPX_SECRET = "test-secret-key-for-trusted-proxy-settings-1234567890"
TPX_FORWARD = ("10.0.1.2", "203.0.113.21")
TPX_DEFAULT = ("10.0.3.2", "203.0.113.23")
TPX_COUNTED = ("10.0.4.2", "203.0.113.24", "203.0.113.25")
TPX_UNCOUNTED = ("10.0.5.2", "203.0.113.26", "203.0.113.27")
TPX_OWN_LIMITS = ("10.0.6.2", "203.0.113.28", "203.0.113.29")
TPX_SHARED = ("10.0.8.2", "203.0.113.30", "203.0.113.31")
TPX_THRESHOLD = 3
TPX_LOGIN_LIMIT = 10
TPX_WRONG_LOGIN = {"email": "nobody@example.com", "password": "Wrong-1234"}
TPX_LIMITED = [401] * 10 + [429]
TPX_PROXY = "10.0.0.2"
TPX_CALLER = "203.0.113.7"
TPX_ADDRESS_CASES = [
    ((TPX_PROXY,), TPX_PROXY),
    ((None, TPX_CALLER), None),
    ((TPX_PROXY, f"{TPX_FORGED}, {TPX_CALLER}, 10.0.0.9"), TPX_CALLER),
    ((TPX_PROXY, TPX_FORGED, TPX_CALLER), TPX_CALLER),
    ((TPX_PROXY, f"{TPX_CALLER}:4711"), TPX_CALLER),
    ((TPX_PROXY, "[2001:db8::7]:4711"), "2001:db8::7"),
    ((f"::ffff:{TPX_PROXY}", TPX_CALLER), TPX_CALLER),
    ((TPX_PROXY, f"{TPX_CALLER}, not-an-address, 10.0.0.9"), "10.0.0.9"),
    ((TPX_PROXY, "10.0.0.8, 10.0.0.9"), "10.0.0.8"),
    ((TPX_PROXY, ""), TPX_PROXY),
    ((TPX_OUTSIDER, TPX_CALLER), TPX_OUTSIDER),
    (("testclient", TPX_CALLER), "testclient"),
]
TPX_DEFAULT_KEY_SCOPES = [
    (TPX_PROXY, TPX_CALLER),
    (TPX_OUTSIDER, TPX_FORGED),
    ("testclient",),
    (None, TPX_CALLER),
]
TPX_KEY_CASES = [
    ((TPX_PROXY, f"{TPX_FORGED}, {TPX_CALLER}"), TPX_CALLER),
    ((TPX_OUTSIDER, TPX_CALLER), TPX_OUTSIDER),
    ((None, TPX_CALLER), "127.0.0.1"),
]
TPX_ENV_NETWORKS = '["10.1.2.3/8", " 2001:db8::/32 ", "192.0.2.1"]'
TPX_LOADED_NETWORKS = ["10.0.0.0/8", "2001:db8::/32", "192.0.2.1/32"]
TPX_NOT_A_NETWORK = ["proxy.example"]
MSG_TPX_FORWARDED = "behind a trusted proxy the {what} request is refused with 401 and recorded with the caller's address"
MSG_TPX_IGNORED = "a forwarded header from an untrusted sender is ignored for the {what} request"
MSG_TPX_EMPTY = "TRUSTED_PROXY_NETWORKS is empty by default"
MSG_TPX_DIRECT = "with the empty default the {what} request is recorded with the direct peer"
MSG_TPX_COUNTED = "behind a trusted proxy repeated refusals are counted by the forwarded address"
MSG_TPX_UNCOUNTED = "without trusted proxies repeated refusals are counted by the proxy"
MSG_TPX_OWN_LIMIT = "behind a trusted proxy the {who} caller has a login limit of its own"
MSG_TPX_NO_ESCAPE = "forged headers from an untrusted sender do not escape its login limit"
MSG_TPX_SHARED = "without trusted proxies the callers behind one proxy share its login limit"
MSG_TPX_ELSEWHERE = "a caller elsewhere keeps a login limit of its own"
MSG_TPX_ADDRESS = (
    "the client address of peer {peer} with forwarded {forwarded} is the right-most untrusted hop"
)
MSG_TPX_DEFAULT_KEY = "with the empty default the rate limit key of {scope} is the direct peer"
MSG_TPX_KEY = "behind a trusted proxy the rate limit key of {scope} is the resolved address"
MSG_TPX_LOADED = "the setting reads a JSON array and normalises each entry to a network"
MSG_TPX_REFUSED = "the setting refuses an entry that is not a network"
CLIS_VERIFIER = "v" * 43
CLIS_CALLBACK = "http://127.0.0.1:8123/callback"
CLIS_CODE_MODE_OFF = "Code sign-in is turned off on this instance. Use callback mode."
CLIS_INVALID = "Invalid or expired authorization. Request a new sign-in link from your client."
CLIS_BAD_REDIRECTS = [
    "https://127.0.0.1:8123/callback",
    "http://example.com:8123/callback",
    "http://127.0.0.2:8123/callback",
    "http://localhost.evil.test:8123/callback",
    "http://localhost/callback",
    "http://localhost:0/callback",
    "http://localhost:65536/callback",
    "http://localhost:port/callback",
    "http://user:password@localhost:8123/callback",
    "http://127.0.0.1:80@evil.test/callback",
    "http://localhost:8123/callback#fragment",
    "http://localhost:8123/callback?code=existing",
    "http://localhost:8123/callback?state=existing",
    "http://localhost:8123/callback?%63ode=existing",
    "http://localhost:8123/callback?STATE=existing",
    "http://localhost:8123/callback?code",
    "http://localhost:8123/callback?x=a&state=b",
    "http://127.1:8123/callback",
    "http://2130706433:8123/callback",
    "//localhost:8123/callback",
    "http://localhost:8123/call\\back",
    "http://local\nhost:8123/callback",
    "http://localhost:8123/call back",
]
CLIS_BAD_STARTS = [
    {"code_challenge": "short"},
    {"code_challenge": "a" * 42 + "="},
    {"code_challenge": "a" * 44},
    {"state": ""},
    {"state": "s" * 129},
    {"client_name": " "},
    {"client_name": "c" * 101},
    {"mode": "callback"},
    {"mode": "other"},
    {"mode": "code", "redirect_uri": "http://localhost:8123/callback"},
    {"extra": "field"},
]
CLIS_BAD_VERIFIERS = ["x" * 43, "short", "x" * 129, "+" * 43]
CLIS_BINDINGS = [None, True, "1", -1, 999999]
CLIS_MUTATIONS = ["expired", "purpose", "user", "version"]
CLIS_WRONG_VERIFIER = "w" * 43
CLIS_WRONG_CODE = "AAAA-AAAA"
CLIS_EVIL_CALLBACK = "https://evil.test/callback"
CLIS_PUBLIC_LIMITS = [("start", 10), ("exchange", 30), ("refresh", 30)]
CLIS_SIGNED_IN_LIMITS = [("check", 30), ("approve", 10)]
MSG_CLIS_REDIRECT = "the callback {uri!r} is refused with 422"
MSG_CLIS_START = "a start with {change} is refused with 422"
MSG_CLIS_PKCE = (
    "the verifier {verifier!r} is refused with 400 or 422, issues no token and consumes nothing"
)
MSG_CLIS_PKCE_KEPT = "after the refused verifiers the right one still exchanges with 200"
MSG_CLIS_LENGTHS = "codes over 256 characters are refused with 422 and 256 with 400; refresh tokens likewise with 422 and 401"
MSG_CLIS_REJECTED = "an unapproved session, a wrong code, an unknown session and an unknown lookup are each refused with 400"
MSG_CLIS_REJECTED_AUDIT = (
    "each refused exchange is recorded as a failure with its reason, no actor and no code"
)
MSG_CLIS_STILL = "after the refusals the approved code still exchanges with 200"
MSG_CLIS_EXPIRED = "an expired {state} session refuses lookup, approval and exchange with 400"
MSG_CLIS_DISABLED = "a disabled account's approval is refused with 403, its exchange with 400 and its refresh with 401"
MSG_CLIS_DISABLED_AUDIT = "the refused refresh is recorded as a failure on the user with its reason"
MSG_CLIS_STALE = (
    "an approval whose account changed meanwhile is refused and leaves the session unapproved"
)
MSG_CLIS_BINDING = "a CLI token whose refresh binding is {binding!r} is refused with 401"
MSG_CLIS_MUTATION = "a CLI token whose refresh row is {mutation} is refused with 401"
MSG_CLIS_REFRESH_REJECT = "an unknown refresh token is refused with 401, a missing one with 422, and the failure carries no token"
MSG_CLIS_NO_SECRET = "no record holds the {secret}"
MSG_CLIS_OUTCOMES = "the sign-in records hold both successes and failures"
MSG_CLIS_LIMIT = "the {path} endpoint answers its first {limit} calls and refuses the next with 429"
MSG_CLIS_MODE_OFF_START = (
    "with code sign-in off a code start is refused with 403 and stores nothing"
)
MSG_CLIS_MODE_OFF_CALLBACK = (
    "with code sign-in off a callback sign-in is looked up, approved, exchanged and denied"
)
MSG_CLIS_MODE_OFF_STORED = (
    "with code sign-in off every stored code request refuses lookup and approval with 403"
)
MSG_CLIS_MODE_OFF_EXCHANGE = "with code sign-in off an approved code request refuses its exchange with 400 and issues no token"
MSG_CLIS_MODE_OFF_AUDIT = "each refusal is recorded with the reason code_mode_disabled, and the requests stay stored and unapproved"
MSG_CLIS_MODE_OFF_MISSING = (
    "with code sign-in off a missing request keeps the answers and reasons of a missing request"
)
MSG_CLIS_MODE_OFF_DENY = "with code sign-in off a stored code request can still be denied, which removes it and is recorded"
MSG_CLIS_DENY_GUARD = "a deny without a sign-in or for an unknown account is refused with 401, an extra or missing field with 422"
MSG_CLIS_DENY_GUARD_STATE = "the refused denies remove nothing and record nothing"
MSG_CLIS_DENY_NOT_PENDING = (
    "a deny of an approved, an expired and an unknown request is refused with 400"
)
MSG_CLIS_DENY_NOT_PENDING_AUDIT = "each refused deny is recorded as not pending, nothing is removed, and the approved code still exchanges"
MSG_CLIS_DENY_AUDIENCE = "any signed-in account may deny or approve, and is recorded as the actor"
MSG_CLIS_DENY_CALLBACK = (
    "a stored callback that is no longer valid cannot be denied and stays stored"
)
MSG_CLIS_DENY_NO_LIMIT = "twelve denies of an unknown request are each answered 400, never 429"
MSG_CLIS_MISMATCH = "a wrong typed code is refused on check and approve with 400, the right one passes the check with 204"
MSG_CLIS_MISMATCH_AUDIT = (
    "both wrong codes are recorded as mismatches, and only the later approval succeeds"
)
MSG_CLIS_RACE = (
    "a request approved elsewhere after its code check is refused with 400 as not pending"
)
ABL_HEAD = "d20260731a09"
ABL_BASELINE = "d20260731a09_locked_baseline_schema.py"
ABL_ROOT_MARKERS = ("down_revision: Union[str, Sequence[str], None] = None", "down_revision = None")
ABL_CORE_TABLES = ["users", "projects", "requirements", "defects", "change_requests"]
ABL_KEPT_INDEXES = [
    "ix_defects_project_id",
    "ix_artefact_links_project_types",
    "pg_trgm",
    "gin_trgm_ops",
]
MSG_ABL_ROOT = "the locked baseline is the only revision without a parent"
MSG_ABL_PARENT = "{name} names a parent revision"
MSG_ABL_NO_CREATE_ALL = "{name} does not rebuild the schema from the models"
MSG_ABL_HEAD = "the baseline keeps the deployed head id and has no parent"
MSG_ABL_EXPLICIT = "the baseline creates its tables with explicit DDL and never calls create_all"
MSG_ABL_TABLE = "the baseline creates the {table} table"
MSG_ABL_INDEX = "the baseline keeps {index}, which the models do not declare"
MSG_ABL_ENUMS = "the baseline drops its enum types on downgrade"
ACL_REFERENCED = "referenced.txt"
ACL_FRESH = "fresh.txt"
ACL_OLD = "old.txt"
ACL_MISSING = "missing.txt"
ACL_GRACE_SECONDS = 3600
ACL_OLD_AGE_SECONDS = 2 * 60 * 60
MSG_ACL_COUNTS = "the reconciliation counts one orphan file and one missing file"
MSG_ACL_FILES = "the referenced and the fresh orphan file stay, the old orphan file is removed"
MSG_ACL_COMMITTED = "the reconciliation commits its session"
MSG_ACL_LIFESPAN = "the application start runs the reconciliation once with its session"
MDI_FRONTMATTER = "---\ntype: requirement\n---\n# Login\nMust work."
MDI_TAGGED = "## [REQ] Boot fast\nbody a\n## [DES] Boot design\nbody b"
MDI_UNMARKED = "# Untagged\nsome text"
MDI_WRAPPED = (
    "## [REQ] Boot\n"
    "Boot within {{parameter: BOOT_MS, value: 500}} ms of power-on, "
    "below {{parameter: MAX_TEMP, value: 85C}}.\n"
)
MDI_REFERENCE = "## [REQ] Boot\nBoot within {{BOOT_MS}} ms.\n"
MDI_HEADING = "## [REQ] Boot in {{parameter: BOOT_MS, value: 500}} ms\n"
MDI_TEST_CASE = (
    "## [TC] Boot within budget\n"
    "Measures the cold boot time of the device under test.\n"
    "- Pre-Condition: device under test powered off through the relay\n"
    "- Loop: repeat {{parameter: BOOT_CYCLES, value: 3}} times\n"
    "  - Step: switch the relay on => relay reports closed\n"
    "  - Step: measure the time from relay on to boot banner => within "
    "{{parameter: BOOT_BUDGET_MS, value: 500}} ms +- "
    "{{parameter: BOOT_TOLERANCE_MS, value: 50}} ms\n"
)
MDI_TEST_CASE_ROWS = [
    ("precondition", "Pre-Condition", 0, "device under test powered off through the relay", ""),
    ("loop", "Loop", 0, "repeat {{BOOT_CYCLES}} times", ""),
    ("step", "Step", 1, "switch the relay on", "relay reports closed"),
    (
        "step",
        "Step",
        1,
        "measure the time from relay on to boot banner",
        "within {{BOOT_BUDGET_MS}} ms +- {{BOOT_TOLERANCE_MS}} ms",
    ),
]
MDI_STRAY_STEP = "## [REQ] Boot\n- Step: not a test case row\n"
MSG_MDI_FRONTMATTER = "the frontmatter type sets the document and section type"
MSG_MDI_TAGGED = "a heading tag classifies its own section"
MSG_MDI_DEFAULT = "an unmarked document takes the default type"
MSG_MDI_WRAPPED = "parameters written in a sentence become placeholders and are collected"
MSG_MDI_REFERENCE = "an existing parameter reference is left alone and collects nothing"
MSG_MDI_HEADING = "a parameter in a heading is replaced and collected"
MSG_MDI_COLLISION = "a parameter whose name exists in any case is reported as a collision"
MSG_MDI_TEST_CASE = (
    "test case lines become step rows with their type, indent, description and expected result"
)
MSG_MDI_STRAY = "step lines outside a test case stay text"
PID_NAME = "Bloom PLM"
PID_IDENTITY = "Bloom PLM by EmbedLabs"
PID_POWERED_BY = "Powered by EmbedLabs"
PID_RENAMED = "Renamed"
PID_INVITE = {
    "to_email": "ada@example.com",
    "full_name": "Ada",
    "invite_link": "https://bloom.example/i#t",
}
PID_ACCESS = {
    "to_email": "admin@example.com",
    "admin_name": "Admin",
    "requester_name": "Ada",
    "requester_email": "ada@example.com",
    "resource": "Requirements",
    "project": "PRJ",
    "requested_at": "2026-10-19 10:00 UTC",
    "request_id": "7",
    "review_link": "https://bloom.example/access",
}
PID_AUTHORIZATION = {
    "to_email": "admin@example.com",
    "full_name": "Admin",
    "old_email": "admin@example.com",
    "new_email": "new@example.com",
    "confirm_link": "https://bloom.example/c#t",
}
PID_SEPARATE_LINK = "Bloom PLM will send a separate verification link"
MSG_PID_CONSTANTS = "the product name, identity and footer are fixed"
MSG_PID_INVITE = "the invitation names Bloom PLM in its subject, title, heading and text"
MSG_PID_ACCESS = "the access request mail names Bloom PLM and leaves no identity placeholder"
MSG_PID_AUTHORIZATION = "the email change authorization names Bloom PLM in its text and HTML"
MSG_PID_API = "the API title and description are the fixed identity"
MSG_PID_NOT_A_SETTING = "BLOOM_APP_NAME is not a setting, from the environment or a dotenv file"
MSG_PID_ENVIRONMENT = "BLOOM_APP_NAME in the environment does not rename the application"
ETC_PREFIX = "PRJ"
ETC_FIRST = "PRJ-TC-001"
ETC_SECOND = "PRJ-TC-002"
ETC_MISSING_PROJECT = 99
MSG_ETC_CSV = "the CSV export has its file name, header and the steps of the first test case"
MSG_ETC_MARKDOWN = "the Markdown export has its file name, title, heading, precondition and step"
MSG_ETC_XML = "the XML export is well formed and lists both test cases in order"
MSG_ETC_MISSING = "an export of a missing project is refused with 404"
JIN_ADF = {
    "type": "doc",
    "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Found by PRJ-TC-004"}]},
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "line one"},
                                {"type": "hardBreak"},
                                {"type": "mention", "attrs": {"text": "@Ada"}},
                            ],
                        }
                    ],
                }
            ],
        },
    ],
}
JIN_BUG = {"issuetype": {"name": "Bug"}, "labels": ["bench"]}
JIN_TASK = {"issuetype": {"name": "Task"}}
JIN_REFERENCE_FIELD = "customfield_1"
JIN_REFERENCES = {
    "summary": "prj-tc-002 fails",
    "customfield_1": "PRJ-TC-002, PRJ-TC-009, ABC-TC-001",
}
JIN_JQL_FULL = (
    'project = "PROJ" AND issuetype in ("Bug", "Say \\"hi\\"") AND statusCategory != Done '
    'AND labels = "bench" AND (priority = High) ORDER BY created ASC'
)
JIN_JQL_DEFAULT = (
    'project = "PROJ" AND issuetype in ("Bug") AND statusCategory != Done ORDER BY created ASC'
)
JIN_URL = "https://acme.atlassian.net/browse/PROJ-7"
MSG_JIN_TEXT = "Atlassian document text is flattened to plain lines"
MSG_JIN_FILTER = "the filter takes bugs by default and honours the issue types and the label"
MSG_JIN_PRIORITY = "Jira priorities map to Bloom levels, with the setting's own map first"
MSG_JIN_RESOLVED = "an issue with a resolution is resolved, one without is not"
MSG_JIN_REFERENCES = (
    "test case ids are read from the summary and description, and from the reference field when set"
)
MSG_JIN_JQL = "the JQL names the project, the types, open issues, the label and the extra clause"
MSG_JIN_FIELDS = "the search asks for the reference field and builds the issue link"
CPY_SOURCE = ("Demo", "PRJ")
CPY_TARGET = ("ABC", "ABC")
CPY_MISSING_ID = 99999
CPY_COPIED_REQ = "ABC-REQ-008"
CPY_COPIED_TC = "ABC-TC-001"
MSG_CPY_COUNTS = "one requirement is copied after the target's highest id and the missing one is skipped with an error"
MSG_CPY_FIELDS = "the copy keeps title, description, priority, type and origin"
MSG_CPY_SOURCE = "the copy is a draft that names its source requirement and project"
MSG_CPY_NEXT = "the next requirement number of the target follows the copy"
MSG_CPY_TEST_CASE = (
    "a copied test case keeps its preconditions and steps, as a draft naming its source"
)
ITC_UPDATE_CSV = (
    "tc_id,title,status,visibility,preconditions,steps,description\n"
    "PRJ-TC-001,Updated login,Draft,internal,User exists,1. Open => Form,Round-trip\n"
    ",Brand new case,Draft,internal,,1. Do X => Y,New one\n"
)
ITC_APPROVE_CSV = (
    "tc_id,title,status\nPRJ-TC-001,Unreviewed change,Approved\n,Unreviewed new case,Approved\n"
)
ITC_XML = (
    '<?xml version="1.0"?><test-cases>'
    '<test-case id="X"><title>From XML</title><status>Draft</status>'
    "<steps>1. Click => Opens</steps></test-case></test-cases>"
)
ITC_NO_TITLE_CSV = "tc_id,title,steps\n,,1. x\n"
MSG_ITC_UPDATE = "a CSV import updates the existing test case and creates the new one"
MSG_ITC_UPDATED = "the updated test case has its new title, stays a draft and has its step"
MSG_ITC_NO_APPROVAL = "a CSV import that sets Approved is skipped and changes nothing"
MSG_ITC_XML = "an XML import creates the test case with its step and a project id"
MSG_ITC_NO_TITLE = "a row without a title is skipped with its error"
PAS_PROJECT_RESOURCES = [
    "baseline",
    "parameter",
    "link",
    "project",
    "users",
    "access",
    "application",
]
PAS_NO_APPROVAL = ["STD", "RSK", "CMP"]
PAS_NO_EXTRA_REVIEW = ["RPT", "STD", "RSK", "CMP"]
PAS_OTHER_ACTIONS = ["view", "comment", "create", "edit", "approve", "delete"]
MSG_PAS_WRITE = "write gives create, edit and view but not review, approve or delete"
MSG_PAS_APPROVE = "approve and delete give review, approve and delete and nothing else"
MSG_PAS_WRITE_READ = "write includes read and comment without approve, review or delete"
MSG_PAS_STORED = "a stored edit reads as view, comment and edit without changing the stored matrix"
MSG_PAS_REVIEW = "review alone on {resource} grants review and no other action"
MSG_PAS_ROUNDTRIP = "a review rule is stored and shown back as review only"
MSG_PAS_ORIGIN = "a review rule without a tag is refused"
MSG_PAS_PROJECT = "review is refused on {resource}"
MSG_PAS_EXCEPTION = "approve is refused on {resource}"
MSG_PAS_EXTERNAL = "external readers may review but never approve or delete"
MSG_PAS_NO_EXTRA = "write and approve on {resource} do not add review"
MSG_PAS_TERM = "an external review term keeps review and the customer scope only"
TCS_EDITOR_ROWS = [
    ("precondition", "device under test powered off through the relay", "", 0),
    ("loop", "repeat {{BOOT_CYCLES}} times", "", 0),
    ("step", "switch the relay on", "relay reports closed", 1),
    (
        "step",
        "measure the time from relay on\nto the boot banner",
        "within {{BOOT_BUDGET_MS}} ms\n+- {{BOOT_TOLERANCE_MS}} ms",
        1,
    ),
]
TCS_FIRST_LINES = [
    "- Pre-Condition: device under test powered off through the relay",
    "- Loop: repeat {{BOOT_CYCLES}} times",
    "  - Step: switch the relay on => relay reports closed",
]
TCS_ROW_KEYS = [
    "collapsed",
    "description",
    "expected_result",
    "id",
    "indent_level",
    "label",
    "row_type",
]
MSG_TCS_TEXT = "editor rows are written as text and read back as the same rows"
MSG_TCS_CONTRACT = "a row read from text has the editor's fields and starts expanded with an id"
MSG_TCS_LEGACY_WRITE = "older stored steps are still written as step lines"
MSG_TCS_LEGACY_READ = "older numbered text is still read as steps"
MSG_TCS_EMPTY = "empty step text reads as nothing and nothing writes as empty text"
MSG_TCS_LEADING = "text before the first row becomes a step"
MSG_TCS_XML = "the XML export reimports with the same rows"
MSG_TCS_MARKDOWN = "the Markdown export reimports as the same test case"
MSG_TCS_PRECONDITION = "plain preconditions become a precondition row in the Markdown export"
EXR_REQUIREMENT_HEADER = [
    "req_id",
    "title",
    "status",
    "priority",
    "type",
    "origin",
    "visibility",
    "description",
    "created_at",
    "updated_at",
]
EXR_TRACE_HEADER = [
    "req_id",
    "req_title",
    "req_status",
    "covered",
    "tc_id",
    "tc_title",
    "tc_last_execution",
]
EXR_MIN_PDF_BYTES = 800
MSG_EXR_CSV = "the requirements CSV has its file name, header and both requirements"
MSG_EXR_PDF = "the requirements PDF is a PDF of more than 800 bytes"
MSG_EXR_TRACE = "the traceability CSV marks the verified requirement covered and the other not"
MSG_EXR_MISSING = "a requirements export of a missing project is refused with 404"
APS_APP_RESOURCES = ["access", "users"]
APS_APP_PERMISSIONS = {"users": {"view", "create", "edit"}, "access": {"delete"}}
APS_ADMITTED = {"REQ": {"view", "comment", "edit"}, "project": {"view"}}
APS_REPLACED = {"REQ": {"view"}}
APS_BUNDLES = {"REQ": {"view"}, "TC": {"view", "comment", "edit"}}
MSG_APS_APP = "group app rules apply without project admission and give nothing inside a project"
MSG_APS_SCOPE = "a {scope} policy supplies no app terms"
MSG_APS_ADMITTED = (
    "an admitted group gives its content rules and never its app rules inside the project"
)
MSG_APS_REPLACED = "a direct project entry replaces the group's content rules but not its app rules"
MSG_APS_ADMIN_ONLY = "app rules do not open the administrator-only management"
MSG_APS_ADMIN = "an instance administrator holds every permission without a policy"
MSG_APS_BUNDLES = (
    "two direct bundles combine without restoring indirect project rights, and app rules stay"
)
IMR_DIGEST = "sha256:" + "a" * 64
IMR_OTHER = "sha256:" + "b" * 64
IMR_IMAGE = "ghcr.io/mbedlabs/product@sha256:" + "a" * 64
IMR_FLOATING = ["image:v1.0.0", "image:1.0.0", "image:1", "image:1.0", "image:stable"]
IMR_GOOD_REFERENCES = [
    "ghcr.io/mbedlabs/product",
    "ghcr.io/mbedlabs/product:sha-" + "0" * 40,
    "ghcr.io/mbedlabs/product:1.2.0",
    "ghcr.io/mbedlabs/product@sha256:" + "a" * 64,
    "localhost:5000/product:dev",
    "registry:5000/product:dev",
    "registry.example.com:443/team/sub_name/product-name:v1.2.0-rc.1",
]
IMR_BAD_REFERENCES = [
    "",
    "-oProxyCommand=id",
    "--format={{.Name}}",
    "-ghcr.io/mbedlabs/product:dev",
    "product:dev",
    "mbedlabs/product:dev",
    "ghcr.io",
    "ghcr.io/MbedLabs/product:dev",
    "ghcr.io/mbedlabs/product:dev --help",
    "ghcr.io/mbedlabs/product:dev\n--help",
    "ghcr.io/mbedlabs/product:-dev",
    "ghcr.io/mbedlabs/product@sha256:abc",
    "ghcr.io/mbedlabs/product@sha256:" + "A" * 64,
    "ghcr.io/mbedlabs/product:" + "t" * 129,
    "ghcr.io/mbedlabs/product:dev@sha256:" + "a" * 64,
    "ghcr.io//product:dev",
    "registry/product:dev",
    "ghcr.io:99999999/product:dev",
    "ghcr.io:99999/product:dev",
    "ghcr.io:0/product:dev",
    "ghcr.io:\u0665\u0660\u0660\u0660/product:dev",
    "registry:/product:dev",
    None,
]
IMR_COMMIT = "0123456789abcdef0123456789abcdef01234567"
IMR_WORKFLOW_ALIASES = [
    "ghcr.io/mbedlabs/bloom:1.2.0",
    "ghcr.io/mbedlabs/bloom:1.2",
    "ghcr.io/mbedlabs/bloom:1",
    "ghcr.io/mbedlabs/bloom:v1.2.0",
    "ghcr.io/mbedlabs/bloom:stable",
    "ghcr.io/mbedlabs/bloom:latest",
    "ghcr.io/mbedlabs/bloom:dev",
    "ghcr.io/mbedlabs/bloom:main",
    "ghcr.io/mbedlabs/bloom:1.3.0-beta.1",
]
MSG_IMR_OLDER = "an older release moves only its own version tags"
MSG_IMR_CURRENT = "the current release may promote stable"
MSG_IMR_STALE = "a stale branch run does not promote latest"
MSG_IMR_PRERELEASE = "a prerelease does not promote stable"
MSG_IMR_CONFLICT = "a version tag on another digest aborts the promotion before any tag moves"
MSG_IMR_REPEAT = "a repeated promotion retags each alias with the same image"
MSG_IMR_MISMATCH = "a digest that differs after promotion fails the promotion"
MSG_IMR_GOOD = (
    "the well-formed reference {reference!r} is inspected once with the exact docker command"
)
MSG_IMR_BAD = "the malformed reference {reference!r} is refused before docker runs"
MSG_IMR_MISSING = "a missing image reports no digest"
MSG_IMR_WORKFLOW = "every reference shape the workflow produces is inspected and promoted"
