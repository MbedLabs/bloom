"""
* @file     ${tests/api/BLOOM_documents_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external member sees customer documents and gets not found for internal ones.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests one customer and one internal document seen by an external member.
"""

from tests.api.documents_external_visibility import DocumentsExternalVisibilityBase


class DocumentsExternalVisibilityTest(DocumentsExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        external_id = self.bloom.bloom_add_account(
            self.parameters.EXTERNAL_EMAIL,
            self.parameters.API_PASSWORD,
            self.parameters.EXTERNAL_ROLE,
        )
        project_id = self.bloom.bloom_create_project(self.parameters.VISIBILITY_PREFIX)
        self.bloom.bloom_add_external_member(
            project_id,
            external_id,
            self.parameters.EXTERNAL_PERMISSIONS,
            self.parameters.CUSTOMER_VISIBILITY,
        )
        self.bloom.bloom_add_document(
            project_id,
            self.parameters.CUSTOMER_DOC_ID,
            self.parameters.CUSTOMER_DOC_TITLE,
            self.parameters.CUSTOMER_VISIBILITY,
        )
        internal_id = self.bloom.bloom_add_document(
            project_id,
            self.parameters.INTERNAL_DOC_ID,
            self.parameters.INTERNAL_DOC_TITLE,
            self.parameters.INTERNAL_VISIBILITY,
        )
        external, self.tc_sign_in = self.bloom.bloom_log_in(
            self.parameters.EXTERNAL_EMAIL, self.parameters.API_PASSWORD
        )
        self.tc_listed = self.bloom.bloom_api_list_documents(external, project_id)
        self.tc_internal = self.bloom.bloom_api_get_document(external, internal_id)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentsExternalVisibilityTest().run()
