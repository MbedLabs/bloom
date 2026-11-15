"""
* @file     ${tests/logic/BLOOM_integration_sync_outages.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    GitHub rate limits and outages are run errors.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests one sync pass over five GitHub integrations, each refused differently.
"""

from tests.logic.integration_sync_outages import IntegrationSyncOutagesBase


class IntegrationSyncOutagesTest(IntegrationSyncOutagesBase):

    def setUpClass(self):
        super().setUpClass()
        number = self.parameters.GIT_NUMBERS[0]
        self.tc_setting_ids = []
        answers = {}
        for index, answer in enumerate(self.parameters.OUTAGES):
            repo = f"{self.parameters.REPO}{index}"
            project_id = self.bloom.bloom_create_project(
                f"{self.parameters.SYNC_PROJECT_PREFIX}{index}"
            )
            self.tc_setting_ids.append(self.bloom.bloom_create_integration(project_id, "github"))
            self.bloom.bloom_link_defect(project_id, "github", repo, number)
            answers[repo] = answer
        self.bloom.bloom_serve_by_repo(answers)
        self.tc_synced = self.bloom.bloom_run_sync(self.parameters.NOW)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSyncOutagesTest().run()
