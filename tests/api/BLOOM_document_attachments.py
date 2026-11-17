"""
* @file     ${tests/api/BLOOM_document_attachments.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Files are stored, read and removed against a document, and Bud publishes each run as one report document.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the attachment and report routes on the full application; each step uses its own project.
"""

from tests.api.document_attachments import DocumentAttachmentsBase


class DocumentAttachmentsTest(DocumentAttachmentsBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_attachment_api()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.token = self.bloom.bloom_api_service_token(self.admin, "bud-publish")

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentAttachmentsTest().run()
