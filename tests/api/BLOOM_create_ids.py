"""
* @file     ${tests/api/BLOOM_create_ids.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Creating a requirement, test case or document assigns its public id on the server.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests three create routes of the full app in-process.
"""

from tests.api.create_ids import CreateIdsBase


class CreateIdsTest(CreateIdsBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        self.admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        self.project_id = (
            self.bloom.bloom_api_create_project(self.admin, self.parameters.CREATE_ID_PREFIX)
            .json()
            .get("id")
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CreateIdsTest().run()
