"""Set-up of the in-process suites: routes and roles of the Bloom under test."""

import re
from pathlib import Path


class BaselinesHttp:
    """Set-up of the baselines_http suite."""

    BASE_URL = "http://test"
    LOGIN_ROUTE = "/api/auth/login"
    USERS_ROUTE = "/api/users"
    PROJECTS_ROUTE = "/api/projects"
    POLICIES_ROUTE = "/api/policies"
    GROUPS_ROUTE = "/api/groups"
    GRANTS_ROUTE = "/api/groups/{group_id}/grants"
    MEMBERS_ROUTE = "/api/groups/{group_id}/members"
    REQUIREMENTS_ROUTE = "/api/requirements"
    DOCUMENTS_ROUTE = "/api/projects/{project_id}/documents"
    BASELINES_ROUTE = "/api/baselines"
    BASELINE_ROUTE = "/api/baselines/{baseline_id}"
    READER_ROLE = "maintainer"


class UiCliAuth:
    """Set-up of the ui_cli_auth suite."""

    DIST = Path(__file__).resolve().parents[2] / "ui" / "dist"
    HOST = "127.0.0.1"
    PAGE_ROUTE = "/auth/cli?session_id={session_id}"
    API_PATTERN = "**/api/**"
    LOOPBACK_PATTERN = re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?/callback")
    REFRESH_PATH = "/api/auth/refresh"
    ME_PATH = "/api/auth/me"
    SETUP_PATH = "/api/setup/status"
    SESSION_PATH = "/api/auth/cli/sessions/{session_id}"
    CHECK_PATH = "/api/auth/cli/check"
    APPROVE_PATH = "/api/auth/cli/approve"
    DENY_PATH = "/api/auth/cli/deny"
    JSON = "application/json"
    HTML = "text/html"
    CLIPBOARD = ["clipboard-read", "clipboard-write"]
    FAILING_CLIPBOARD = "navigator.clipboard.writeText = () => Promise.reject(new Error('denied'))"
    TIMEOUT_MS = 10000
    SETTLE_MS = 500
