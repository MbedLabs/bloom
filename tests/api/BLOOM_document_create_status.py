"""
* @file     ${tests/api/BLOOM_document_create_status.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A document is created in Draft; naming another first status answers 422.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the document create route of the full app in-process.
"""

from tests.api.document_create_status import DocumentCreateStatusBase


class DocumentCreateStatusTest(DocumentCreateStatusBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        self.admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        self.project_id = (
            self.bloom.bloom_api_create_project(self.admin, self.parameters.DOC_STATUS_PREFIX)
            .json()
            .get("id")
        )
        self.path = f"/api/projects/{self.project_id}/documents"

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentCreateStatusTest().run()
