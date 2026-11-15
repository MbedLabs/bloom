"""
* @file     ${tests/api/BLOOM_create_ids.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Creating a requirement, test case or document assigns its public id on the server.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests three create routes of the full app in-process.
"""

from types import SimpleNamespace

from tests.api.create_ids import CreateIdsBase


class CreateIdsTest(CreateIdsBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project_id = (
            self.bloom.bloom_api_create_project(admin, self.parameters.CREATE_ID_PREFIX)
            .json()
            .get("id")
        )
        self.tc_pattern = self.bloom.bloom_doc_id_pattern()
        self.tc_created = {}
        for path, payload, id_field, type_code in self.parameters.CREATE_ID_CASES:
            answer = self.bloom.bloom_api_call(
                "POST",
                path.format(project_id=project_id),
                admin,
                json={"project_id": project_id, **payload},
            )
            self.tc_created[type_code] = SimpleNamespace(
                status=answer.status, public_id=(answer.body or {}).get(id_field)
            )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CreateIdsTest().run()
