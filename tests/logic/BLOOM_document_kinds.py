"""
* @file     ${tests/logic/BLOOM_document_kinds.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Shared-document kinds normalize legacy values and accept only canonical codes.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests legacy values, public API values, route slugs and link counts.
"""

from tests.logic.document_kinds import DocumentKindsBase


class DocumentKindsTest(DocumentKindsBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentKindsTest().run()
