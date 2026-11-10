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
    "tests.pg.BLOOM_integration_sync_race.IntegrationSyncRaceTest",
]
