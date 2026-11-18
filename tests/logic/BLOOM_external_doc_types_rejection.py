"""
* @file     ${tests/logic/BLOOM_external_doc_types_rejection.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external member is refused a document type their term does not grant.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the access check for a document type outside the grant.
"""

from tests.logic.external_doc_types_rejection import ExternalDocTypesRejectionBase


class ExternalDocTypesRejectionTest(ExternalDocTypesRejectionBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExternalDocTypesRejectionTest().run()
