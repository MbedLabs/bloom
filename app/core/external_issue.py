"""Validation and normalization for external issue tracker references."""

import re
from typing import Optional

GITHUB_ISSUE_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<number>\d+)"
)
GITLAB_ISSUE_URL_RE = re.compile(
    r"^https?://(?P<host>[^/]+)/(?P<namespace>.+?)/-/issues/(?P<iid>\d+)"
)

SUPPORTED_TRACKERS = frozenset({"github", "gitlab"})


class ExternalIssueRef:
    __slots__ = ("tracker", "repo_full_name", "issue_number", "url")

    def __init__(
        self,
        tracker: str,
        repo_full_name: str,
        issue_number: int,
        url: str,
    ):
        self.tracker = tracker
        self.repo_full_name = repo_full_name
        self.issue_number = issue_number
        self.url = url


def parse_github_url(url: str) -> Optional[ExternalIssueRef]:
    m = GITHUB_ISSUE_URL_RE.match(url.strip())
    if not m:
        return None
    return ExternalIssueRef(
        tracker="github",
        repo_full_name=f"{m.group('owner')}/{m.group('repo')}",
        issue_number=int(m.group("number")),
        url=url.strip(),
    )


def parse_gitlab_url(url: str) -> Optional[ExternalIssueRef]:
    m = GITLAB_ISSUE_URL_RE.match(url.strip())
    if not m:
        return None
    return ExternalIssueRef(
        tracker="gitlab",
        repo_full_name=m.group("namespace"),
        issue_number=int(m.group("iid")),
        url=url.strip(),
    )


def parse_issue_url(url: str) -> Optional[ExternalIssueRef]:
    return parse_github_url(url) or parse_gitlab_url(url)


def validate_external_fields(
    tracker: Optional[str],
    url: Optional[str],
    repo_full_name: Optional[str],
    issue_number: Optional[int],
) -> Optional[str]:
    """Return an error message if fields are inconsistent, or None if valid."""
    if tracker and tracker not in SUPPORTED_TRACKERS:
        return (
            f"Unsupported tracker '{tracker}'. Supported: {', '.join(sorted(SUPPORTED_TRACKERS))}"
        )

    if url:
        parsed = parse_issue_url(url)
        if not parsed:
            return "Cannot parse external issue URL. Expected a GitHub or GitLab issue URL."
        if tracker and parsed.tracker != tracker:
            return f"URL belongs to {parsed.tracker} but tracker is set to {tracker}"
        if repo_full_name and parsed.repo_full_name != repo_full_name:
            return (
                f"URL repo '{parsed.repo_full_name}' does not match "
                f"provided repo '{repo_full_name}'"
            )
        if issue_number is not None and parsed.issue_number != issue_number:
            return (
                f"URL issue #{parsed.issue_number} does not match "
                f"provided issue #{issue_number}"
            )

    return None
