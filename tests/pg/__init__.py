"""The Bloom suites of tests/pg, as bud-runner run-tests -t tests.pg.SUITES runs them."""

import tests.config  # noqa: F401

SUITES = [
    "tests.pg.BLOOM_campaign_public_id_duplicates.CampaignPublicIdDuplicatesTest",
    "tests.pg.BLOOM_campaign_public_id_migration.CampaignPublicIdMigrationTest",
    "tests.pg.BLOOM_cli_auth_concurrent_approval.CliAuthConcurrentApprovalTest",
    "tests.pg.BLOOM_cli_auth_deny_approve_race.CliAuthDenyApproveRaceTest",
    "tests.pg.BLOOM_cli_auth_migration_fresh.CliAuthMigrationFreshTest",
    "tests.pg.BLOOM_cli_auth_migration_round_trip.CliAuthMigrationRoundTripTest",
    "tests.pg.BLOOM_cli_auth_refresh_revocation.CliAuthRefreshRevocationTest",
    "tests.pg.BLOOM_document_assignee_migration.DocumentAssigneeMigrationTest",
    "tests.pg.BLOOM_document_workflow_concurrency.DocumentWorkflowConcurrencyTest",
    "tests.pg.BLOOM_document_workflow_migration.DocumentWorkflowMigrationTest",
    "tests.pg.BLOOM_id_widening.IdWideningTest",
    "tests.pg.BLOOM_integration_sync_race.IntegrationSyncRaceTest",
    "tests.pg.BLOOM_integrity_conflict.IntegrityConflictTest",
    "tests.pg.BLOOM_link_rules_enforcement.LinkRulesEnforcementTest",
    "tests.pg.BLOOM_pre_baseline_repair.PreBaselineRepairTest",
    "tests.pg.BLOOM_refresh_flow.RefreshFlowTest",
    "tests.pg.BLOOM_repeated_refusals.RepeatedRefusalsTest",
    "tests.pg.BLOOM_requirement_parent_drop_migration.RequirementParentDropMigrationTest",
    "tests.pg.BLOOM_requirement_text_migration.RequirementTextMigrationTest",
    "tests.pg.BLOOM_session_invalidation.SessionInvalidationTest",
    "tests.pg.BLOOM_token_concurrency.TokenConcurrencyTest",
]
