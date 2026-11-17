"""
* @file     ${tests/api/BLOOM_document_workflow_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Real HTTP handoffs bind review, approval and archived content to their actors.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the workflow routes on the full application with four administrators; each case starts from a new database.
"""

from tests.api.document_workflow_http import DocumentWorkflowHttpBase


class DocumentWorkflowHttpTest(DocumentWorkflowHttpBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_workflow_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentWorkflowHttpTest().run()
