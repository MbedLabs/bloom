"""
* @file     ${tests/logic/BLOOM_integration_sync_settings_response.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The settings response carries the sync state and the integration's own rate.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests the settings API answer of an integration with a recorded sync.
"""

from tests.logic.integration_sync_settings_response import (
    IntegrationSyncSettingsResponseBase,
)


class IntegrationSyncSettingsResponseTest(IntegrationSyncSettingsResponseBase):

    def setUpClass(self):
        super().setUpClass()
        created, updated = self.parameters.PREVIOUS_COUNTS
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id,
            sync_checked_at=self.parameters.NOW,
            synced_at=self.parameters.NOW,
            sync_warning=self.parameters.WARNING_TEXT,
            sync_created=created,
            sync_updated=updated,
            auto_sync_minutes=self.parameters.SYNC_RATE,
        )
        self.tc_response = self.bloom.bloom_get_setting_response(self.tc_setting_id)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncSettingsResponseTest().run()
