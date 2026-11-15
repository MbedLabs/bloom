"""
* @file     ${tests/logic/BLOOM_integration_sync_settings_left_alone.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Integrations not due, disabled or without credentials are left alone.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one sync pass over three integrations none of which may sync.
"""

from tests.logic.integration_sync_settings_left_alone import (
    IntegrationSyncSettingsLeftAloneBase,
)


class IntegrationSyncSettingsLeftAloneTest(IntegrationSyncSettingsLeftAloneBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_recent_id = self.bloom.bloom_create_integration(
            self.bloom.bloom_create_project(f"{self.parameters.SYNC_PROJECT_PREFIX}R"),
            sync_checked_at=self.parameters.NOW - self.parameters.RECENT_CHECK,
        )
        self.tc_disabled_id = self.bloom.bloom_create_integration(
            self.bloom.bloom_create_project(f"{self.parameters.SYNC_PROJECT_PREFIX}D"),
            enabled=False,
            jira_project_key=self.parameters.JIRA_OTHER_PROJECT,
        )
        self.tc_tokenless_id = self.bloom.bloom_create_integration(
            self.bloom.bloom_create_project(f"{self.parameters.SYNC_PROJECT_PREFIX}T"),
            "github",
            token_encrypted=None,
        )
        self.bloom.bloom_refuse_with(self.parameters.STATUS_SERVER_ERROR)
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncSettingsLeftAloneTest().run()
