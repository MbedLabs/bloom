"""
* @file     ${tests/parameters.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Constants of Bloom's tests: drawn test data, expected values and messages.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Test data is drawn from SEED; BUDTEST_SEED repeats a run with the same data.
"""

import os
import random
import string
from datetime import datetime, timedelta

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
NOW = datetime(2026, 1, 1) + timedelta(minutes=_draw.randrange(0, 365 * 24 * 60))
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
