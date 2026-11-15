"""
* @file     ${tests/logic/BLOOM_external_doc_types_admin.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An admin sees every document type of a project without a database query.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the document types answered for an admin.
"""

from tests.logic.external_doc_types_admin import ExternalDocTypesAdminBase


class ExternalDocTypesAdminTest(ExternalDocTypesAdminBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_admin = self.bloom.bloom_external_doc_types_as_admin(
            self.parameters.EXTERNAL_PROJECT_ID
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExternalDocTypesAdminTest().run()
