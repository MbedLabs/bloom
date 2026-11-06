"""
* @file     ${tests/logic/BLOOM_integration_sync_reopened_in_bloom.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A defect reopened in Bloom stays open while its GitHub issue stays closed.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one GitHub sync run over a defect reopened in Bloom.
"""

from tests.logic.integration_sync_reopened_in_bloom import (
    IntegrationSyncReopenedInBloomBase,
)


class IntegrationSyncReopenedInBloomTest(IntegrationSyncReopenedInBloomBase):

    def setUpClass(self):
        super().setUpClass()
        number = self.parameters.GIT_NUMBERS[0]
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id, "github")
        self.tc_defect_id = self.bloom.bloom_link_defect(
            self.tc_project_id,
            "github",
            self.parameters.REPO,
            number,
            status=self.parameters.DEFECT_OPEN,
            external_issue_state=self.parameters.GIT_CLOSED,
            external_issue_closed=True,
        )
        self.bloom.bloom_serve_issue_list([{"number": number, "state": self.parameters.GIT_CLOSED}])
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncReopenedInBloomTest().run()
