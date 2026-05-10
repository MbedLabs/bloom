"""Tests for defect-related functionality: link rules, URL validation, webhook signatures."""

import hashlib
import hmac
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.core.external_issue import (
    parse_github_url,
    parse_gitlab_url,
    parse_issue_url,
    validate_external_fields,
)
from app.core.link_rules import (
    get_allowed_link_roles,
    is_allowed_link_role,
    is_known_linkable_type,
)

# ==================== Link rules for DEF and CMP ====================


def test_def_is_known_linkable_type():
    assert is_known_linkable_type("DEF") is True


def test_cmp_is_known_linkable_type():
    assert is_known_linkable_type("CMP") is True


def test_def_to_req_roles():
    roles = get_allowed_link_roles("DEF", "REQ")
    assert "impacts" in roles
    assert "references" in roles


def test_def_to_tc_roles():
    assert get_allowed_link_roles("DEF", "TC") == ("references",)


def test_def_to_def_roles():
    roles = get_allowed_link_roles("DEF", "DEF")
    assert "duplicates" in roles
    assert "relates_to" in roles
    assert "depends_on" in roles


def test_cmp_to_def_roles():
    assert get_allowed_link_roles("CMP", "DEF") == ("references",)


def test_def_to_cmp_roles():
    assert get_allowed_link_roles("DEF", "CMP") == ("references",)


def test_tc_to_def_roles():
    assert get_allowed_link_roles("TC", "DEF") == ("references",)


def test_rpt_to_def_roles():
    assert get_allowed_link_roles("RPT", "DEF") == ("references",)


def test_forbidden_link_pair():
    assert get_allowed_link_roles("DEF", "BL") == ()
    assert is_allowed_link_role("DEF", "BL", "references") is False


def test_chg_to_def_roles():
    roles = get_allowed_link_roles("CHG", "DEF")
    assert "implements" in roles
    assert "references" in roles


# ==================== External issue URL parsing ====================


def test_parse_github_url():
    ref = parse_github_url("https://github.com/octocat/Hello-World/issues/42")
    assert ref is not None
    assert ref.tracker == "github"
    assert ref.repo_full_name == "octocat/Hello-World"
    assert ref.issue_number == 42


def test_parse_github_url_invalid():
    assert parse_github_url("https://github.com/octocat") is None
    assert parse_github_url("https://gitlab.com/group/project/-/issues/1") is None


def test_parse_gitlab_url():
    ref = parse_gitlab_url("https://gitlab.com/mygroup/myproject/-/issues/7")
    assert ref is not None
    assert ref.tracker == "gitlab"
    assert ref.repo_full_name == "mygroup/myproject"
    assert ref.issue_number == 7


def test_parse_gitlab_url_nested_namespace():
    ref = parse_gitlab_url("https://gitlab.example.com/org/sub/project/-/issues/99")
    assert ref is not None
    assert ref.repo_full_name == "org/sub/project"
    assert ref.issue_number == 99


def test_parse_gitlab_url_invalid():
    assert parse_gitlab_url("https://github.com/user/repo/issues/1") is None


def test_parse_issue_url_auto_detects():
    gh = parse_issue_url("https://github.com/owner/repo/issues/10")
    assert gh is not None and gh.tracker == "github"
    gl = parse_issue_url("https://gitlab.com/ns/proj/-/issues/3")
    assert gl is not None and gl.tracker == "gitlab"


# ==================== External field validation ====================


def test_validate_external_fields_valid():
    assert (
        validate_external_fields(
            "github",
            "https://github.com/owner/repo/issues/5",
            "owner/repo",
            5,
        )
        is None
    )


def test_validate_external_fields_tracker_mismatch():
    err = validate_external_fields(
        "gitlab",
        "https://github.com/owner/repo/issues/5",
        None,
        None,
    )
    assert err is not None
    assert "github" in err.lower()


def test_validate_external_fields_repo_mismatch():
    err = validate_external_fields(
        None,
        "https://github.com/owner/repo/issues/5",
        "other/repo",
        None,
    )
    assert err is not None
    assert "repo" in err.lower()


def test_validate_external_fields_number_mismatch():
    err = validate_external_fields(
        None,
        "https://github.com/owner/repo/issues/5",
        None,
        99,
    )
    assert err is not None
    assert "#99" in err or "99" in err


def test_validate_external_fields_unsupported_tracker():
    err = validate_external_fields("jira", None, None, None)
    assert err is not None
    assert "Unsupported" in err


def test_validate_external_fields_bad_url():
    err = validate_external_fields(None, "https://example.com/not-an-issue", None, None)
    assert err is not None
    assert "parse" in err.lower()


def test_validate_external_fields_none_fields():
    assert validate_external_fields(None, None, None, None) is None


# ==================== Webhook signature verification ====================


def test_github_hmac_signature():
    from app.api.integrations import _verify_github_signature

    secret = "my-webhook-secret"
    body = b'{"action":"opened"}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert _verify_github_signature(body, secret, sig) is True
    assert _verify_github_signature(body, secret, "sha256=wrong") is False


def test_gitlab_token_verification():
    from app.api.integrations import _verify_gitlab_token

    assert _verify_gitlab_token("secret-token", "secret-token") is True
    assert _verify_gitlab_token("secret-token", "wrong-token") is False
