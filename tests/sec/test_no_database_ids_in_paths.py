"""Gate: no API route takes a database ID in its path unless a follow-up ticket still owns it.

Every API route with an integer path parameter must be on ``DATABASE_ID_ROUTES``, grouped by
the ticket that moves it to a public ID; each ticket removes its group when its routes change.
``UNASSIGNED`` holds the routes that no ticket owns yet.
"""

from app.main import app
from tests.sec.test_route_auth_matrix import _api_routes

DATABASE_ID_ROUTES: dict[str, frozenset[str]] = {
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


def _is_integer(annotation) -> bool:
    """True for int and its subclasses other than bool."""
    return isinstance(annotation, type) and issubclass(annotation, int) and annotation is not bool


def _integer_path_routes() -> set[str]:
    """Every API route, as METHOD and path, with an integer path parameter."""
    found: set[str] = set()
    for path, route in _api_routes(app):
        if any(_is_integer(param.field_info.annotation) for param in route.dependant.path_params):
            found.update(f"{method} {path}" for method in route.methods or ())
    return found


def _allowlisted() -> set[str]:
    """Every route on the allowlist, whatever its ticket."""
    return set().union(*DATABASE_ID_ROUTES.values())


def test_no_unlisted_api_route_takes_a_database_id_in_its_path():
    unlisted = sorted(_integer_path_routes() - _allowlisted())
    assert unlisted == [], (
        "These API routes take an integer, a database ID, in their path. Address the record by "
        "its public ID instead: " + ", ".join(unlisted)
    )


def test_every_allowlisted_route_still_takes_a_database_id():
    stale = sorted(_allowlisted() - _integer_path_routes())
    assert stale == [], (
        "These routes no longer take an integer in their path; remove them from "
        "DATABASE_ID_ROUTES: " + ", ".join(stale)
    )


def test_each_route_is_owned_by_one_group_only():
    seen: dict[str, str] = {}
    shared = []
    for owner, routes in DATABASE_ID_ROUTES.items():
        for route in routes:
            if route in seen:
                shared.append(f"{route} ({seen[route]}, {owner})")
            seen[route] = owner
    assert shared == []


def test_suite_and_campaign_routes_take_no_database_id():
    owned = [
        route
        for route in _integer_path_routes() | _allowlisted()
        if route.split(" ", 1)[1].startswith(("/api/test-suites", "/api/campaigns"))
    ]
    assert owned == []
