"""The Bloom suites of tests/sec, as bud-runner run-tests -t tests.sec.SUITES runs them."""

import tests.config  # noqa: F401

SUITES = [
    "tests.sec.BLOOM_artefacts_external_visibility.ArtefactsExternalVisibilityTest",
    "tests.sec.BLOOM_baselines_external_visibility.BaselinesExternalVisibilityTest",
    "tests.sec.BLOOM_defect_webhook_security.DefectWebhookSecurityTest",
    "tests.sec.BLOOM_integration_secrets.IntegrationSecretsTest",
    "tests.sec.BLOOM_integrations_settings_redaction.IntegrationsSettingsRedactionTest",
    "tests.sec.BLOOM_nginx_security_headers.NginxSecurityHeadersTest",
    "tests.sec.BLOOM_no_database_ids_in_paths.NoDatabaseIdsInPathsTest",
    "tests.sec.BLOOM_password_policy.PasswordPolicyTest",
    "tests.sec.BLOOM_project_iam.ProjectIamTest",
    "tests.sec.BLOOM_project_variables_external_access.ProjectVariablesExternalAccessTest",
    "tests.sec.BLOOM_route_auth_matrix.RouteAuthMatrixTest",
    "tests.sec.BLOOM_service_credentials.ServiceCredentialsTest",
    "tests.sec.BLOOM_token_logging.TokenLoggingTest",
]
