"""
* @file     ${tests/logic/BLOOM_integration_sync_github_state.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A GitHub issue's state reaches its defect and change request.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one GitHub sync run with closed issues and a closed pull request.
"""

from tests.logic.integration_sync_github_state import IntegrationSyncGithubStateBase


class IntegrationSyncGithubStateTest(IntegrationSyncGithubStateBase):

    def setUpClass(self):
        super().setUpClass()
        defect_number, change_number, pull_number, _ = self.parameters.GIT_NUMBERS
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(self.tc_project_id, "github")
        self.tc_defect_id = self.bloom.bloom_link_defect(
            self.tc_project_id, "github", self.parameters.REPO, defect_number
        )
        self.tc_change_id = self.bloom.bloom_link_change(
            self.tc_project_id,
            "github",
            self.parameters.REPO,
            change_number,
            self.parameters.CHANGE_SUBMITTED,
        )
        self.bloom.bloom_serve_issue_list(
            [
                {
                    "number": defect_number,
                    "state": self.parameters.GIT_CLOSED,
                    "updated_at": self.bloom.bloom_git_time(self.parameters.NOW),
                },
                {"number": change_number, "state": self.parameters.GIT_CLOSED},
                {"number": pull_number, "state": self.parameters.GIT_CLOSED, "pull_request": {}},
            ]
        )
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncGithubStateTest().run()
