"""Set-up of the in-process suites: routes and roles of the Bloom under test."""


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
    DOCUMENTS_ROUTE = "/api/documents"
    BASELINES_ROUTE = "/api/baselines"
    BASELINE_ROUTE = "/api/baselines/{baseline_id}"
    READER_ROLE = "maintainer"
