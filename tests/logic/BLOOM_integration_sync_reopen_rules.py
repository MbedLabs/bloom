"""
* @file     ${tests/logic/BLOOM_integration_sync_reopen_rules.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Only a closed issue that is open again reopens its defect.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one GitHub sync run over three defects whose issues are all open.
"""

from tests.logic.integration_sync_reopen_rules import IntegrationSyncReopenRulesBase


class IntegrationSyncReopenRulesTest(IntegrationSyncReopenRulesBase):

    def setUpClass(self):
        super().setUpClass()
        working, reopened, closed_in_bloom, _ = self.parameters.GIT_NUMBERS
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id, "github")
        self.tc_working_id = self.bloom.bloom_link_defect(
            self.tc_project_id,
            "github",
            self.parameters.REPO,
            working,
            status=self.parameters.DEFECT_IN_PROGRESS,
        )
        self.tc_reopened_id = self.bloom.bloom_link_defect(
            self.tc_project_id,
            "github",
            self.parameters.REPO,
            reopened,
            status=self.parameters.DEFECT_CLOSED,
            external_issue_state=self.parameters.GIT_CLOSED,
            external_issue_closed=True,
        )
        self.tc_closed_in_bloom_id = self.bloom.bloom_link_defect(
            self.tc_project_id,
            "github",
            self.parameters.REPO,
            closed_in_bloom,
            status=self.parameters.DEFECT_CLOSED,
            external_issue_state=self.parameters.GIT_OPEN,
            external_issue_closed=False,
        )
        self.bloom.bloom_serve_issue_list(
            [
                {"number": working, "state": self.parameters.GIT_OPEN},
                {"number": reopened, "state": self.parameters.GIT_OPEN},
                {
                    "number": closed_in_bloom,
                    "state": self.parameters.GIT_OPEN,
                    "title": self.parameters.SAME_SUMMARY,
                },
            ]
        )
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncReopenRulesTest().run()
