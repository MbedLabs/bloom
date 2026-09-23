"""Jira to Bloom defects: which issues a project takes in and what a defect copies.

Pure functions over the Jira issue ``fields`` object, shared by the webhook and the
backfill pull so both produce the same defect from the same issue.
"""

import re
from typing import Any, Optional

DEFAULT_ISSUE_TYPES = ["Bug"]
BLOOM_LEVELS = ("Critical", "High", "Medium", "Low")
DEFAULT_PRIORITY_MAP = {
    "Highest": "Critical",
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
    "Lowest": "Low",
}
REMOVED_STATE = "Removed in Jira"
ISSUE_FIELDS = ["summary", "description", "priority", "status", "issuetype", "labels", "resolution"]
_BLOCKS = {"paragraph", "heading", "listItem", "codeBlock", "blockquote", "tableRow", "rule"}


def adf_to_text(value: Any) -> str:
    """Render a Jira description to plain text: a string as is, an Atlassian Document
    Format tree as its text with one line per block."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    lines: list[str] = []
    current: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return
        kind = node.get("type")
        if kind == "text":
            current.append(node.get("text", ""))
        elif kind == "hardBreak":
            current.append("\n")
        elif kind in ("mention", "emoji"):
            current.append((node.get("attrs") or {}).get("text", ""))
        walk(node.get("content", []))
        if kind in _BLOCKS:
            lines.append("".join(current).strip())
            current.clear()

    walk(value)
    if current:
        lines.append("".join(current).strip())
    return "\n".join(line for line in lines if line).strip()


def issue_types(setting) -> list[str]:
    """The issue types a project takes in; Bug when none is configured."""
    return list(setting.jira_issue_types or DEFAULT_ISSUE_TYPES)


def issue_matches(setting, fields: dict) -> bool:
    """True when the issue's type is one the project takes in and it carries the
    configured label, when one is set."""
    kind = ((fields.get("issuetype") or {}).get("name") or "").lower()
    if kind not in {t.lower() for t in issue_types(setting)}:
        return False
    if setting.jira_label:
        return setting.jira_label in (fields.get("labels") or [])
    return True


def bloom_level(setting, fields: dict) -> str:
    """The Bloom priority for the issue's Jira priority, through the project's map."""
    name = (fields.get("priority") or {}).get("name") or ""
    mapping = {**DEFAULT_PRIORITY_MAP, **(setting.jira_priority_map or {})}
    return mapping.get(name, "Medium")


def is_resolved(fields: dict) -> bool:
    """True when Jira reports a resolution on the issue."""
    return bool(fields.get("resolution"))


def referenced_tc_ids(prefix: str, setting, fields: dict) -> list[str]:
    """Bloom test-case ids of the project named in the summary, the description or
    the configured reference field, in the order they appear."""
    texts = [fields.get("summary") or "", adf_to_text(fields.get("description"))]
    if setting.jira_reference_field:
        texts.append(adf_to_text(fields.get(setting.jira_reference_field)))
    pattern = re.compile(rf"\b{re.escape(prefix)}-TC-\d+\b", re.IGNORECASE)
    found: list[str] = []
    for text in texts:
        for match in pattern.findall(text):
            if match.upper() not in found:
                found.append(match.upper())
    return found


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_jql(setting) -> str:
    """The backfill search: the mapped project, the issue types, the label and the
    JQL fragment, when set."""
    clauses = [
        f"project = {_quote(setting.jira_project_key)}",
        "issuetype in (" + ", ".join(_quote(t) for t in issue_types(setting)) + ")",
    ]
    if setting.jira_label:
        clauses.append(f"labels = {_quote(setting.jira_label)}")
    if setting.jira_jql:
        clauses.append(f"({setting.jira_jql})")
    return " AND ".join(clauses) + " ORDER BY created ASC"


def search_fields(setting) -> list[str]:
    """The issue fields the backfill asks Jira for."""
    extra = [setting.jira_reference_field] if setting.jira_reference_field else []
    return ISSUE_FIELDS + extra


def issue_url(setting, issue_key: str) -> Optional[str]:
    """The browser URL of an issue on the configured site."""
    if not setting.base_url:
        return None
    return f"{setting.base_url.rstrip('/')}/browse/{issue_key}"
