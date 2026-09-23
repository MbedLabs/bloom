"""Jira to Bloom mapping: description text, filter, priority, references and JQL."""

from types import SimpleNamespace

from app.services.jira_inbound import (
    adf_to_text,
    bloom_level,
    build_jql,
    is_resolved,
    issue_matches,
    issue_types,
    issue_url,
    referenced_tc_ids,
    search_fields,
)


def _setting(**overrides):
    values = {
        "jira_issue_types": None,
        "jira_label": None,
        "jira_jql": None,
        "jira_reference_field": None,
        "jira_priority_map": None,
        "jira_project_key": "PROJ",
        "base_url": "https://acme.atlassian.net/",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


ADF = {
    "type": "doc",
    "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Found by ALP-TC-004"}]},
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


def test_adf_to_text():
    assert adf_to_text(None) == ""
    assert adf_to_text("  plain  ") == "plain"
    assert adf_to_text(ADF) == "Found by ALP-TC-004\nline one\n@Ada"
    assert adf_to_text({"type": "text", "text": "loose"}) == "loose"


def test_filter_defaults_to_bugs_and_honours_the_label():
    bug = {"issuetype": {"name": "Bug"}, "labels": ["bench"]}
    task = {"issuetype": {"name": "Task"}}
    assert issue_types(_setting()) == ["Bug"]
    assert issue_matches(_setting(), bug)
    assert not issue_matches(_setting(), task)
    assert issue_matches(_setting(jira_issue_types=["bug", "Task"]), task)
    assert issue_matches(_setting(jira_label="bench"), bug)
    assert not issue_matches(_setting(jira_label="field"), bug)


def test_priority_map_and_resolution():
    assert bloom_level(_setting(), {"priority": {"name": "Highest"}}) == "Critical"
    assert bloom_level(_setting(), {"priority": {"name": "Lowest"}}) == "Low"
    assert bloom_level(_setting(), {}) == "Medium"
    assert (
        bloom_level(_setting(jira_priority_map={"Low": "High"}), {"priority": {"name": "Low"}})
        == "High"
    )
    assert is_resolved({"resolution": {"name": "Fixed"}})
    assert not is_resolved({"resolution": None})


def test_referenced_test_cases():
    fields = {
        "summary": "alp-tc-002 fails",
        "description": ADF,
        "customfield_1": "ALP-TC-002, ALP-TC-009, BMS-TC-001",
    }
    assert referenced_tc_ids("ALP", _setting(), fields) == ["ALP-TC-002", "ALP-TC-004"]
    assert referenced_tc_ids("ALP", _setting(jira_reference_field="customfield_1"), fields) == [
        "ALP-TC-002",
        "ALP-TC-004",
        "ALP-TC-009",
    ]


def test_jql_fields_and_url():
    setting = _setting(
        jira_issue_types=["Bug", 'Say "hi"'], jira_label="bench", jira_jql="priority = High"
    )
    assert build_jql(setting) == (
        'project = "PROJ" AND issuetype in ("Bug", "Say \\"hi\\"") AND labels = "bench" '
        "AND (priority = High) ORDER BY created ASC"
    )
    assert build_jql(_setting()) == 'project = "PROJ" AND issuetype in ("Bug") ORDER BY created ASC'
    assert search_fields(_setting(jira_reference_field="customfield_1"))[-1] == "customfield_1"
    assert issue_url(_setting(), "PROJ-7") == "https://acme.atlassian.net/browse/PROJ-7"
    assert issue_url(_setting(base_url=None), "PROJ-7") is None
