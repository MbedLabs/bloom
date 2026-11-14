"""
* @file     ${tests/pg/BLOOM_integration_sync_race.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Sync now and a scheduled run on one integration at once create one defect per issue.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests both runs searching before either writes, on a new PostgreSQL database.
"""

from tests.pg.integration_sync_race import IntegrationSyncRaceBase


class IntegrationSyncRaceTest(IntegrationSyncRaceBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres()
        if not self.tc_postgres:
            return
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id)
        issue = {
            "key": self.bloom.bloom_jira_key(self.parameters.RACE_ISSUE_NUMBER),
            "fields": {
                "issuetype": {"name": self.parameters.BUG},
                "summary": self.parameters.NEW_SUMMARY,
            },
        }
        self.tc_searches = self.bloom.bloom_serve_jira_holding_creation(issue)
        self.bloom.bloom_race_sync_now_and_scheduled(
            self.tc_setting_id, self.parameters.ADMIN_EMAIL, self.parameters.NOW
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncRaceTest().run()
