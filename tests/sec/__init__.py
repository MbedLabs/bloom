"""The Bloom suites of tests/sec, as bud-runner run-tests -t tests.sec.SUITES runs them."""

import tests.config  # noqa: F401

SUITES = [
    "tests.sec.BLOOM_password_policy.PasswordPolicyTest",
    "tests.sec.BLOOM_project_iam.ProjectIamTest",
    "tests.sec.BLOOM_route_auth_matrix.RouteAuthMatrixTest",
    "tests.sec.BLOOM_token_logging.TokenLoggingTest",
]
