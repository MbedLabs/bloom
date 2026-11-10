"""
* @file     ${tests/logic/BLOOM_external_doc_types_allow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external member is let through to a document type their term grants.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the access check for the granted document type.
"""

from tests.logic.external_doc_types_allow import ExternalDocTypesAllowBase


class ExternalDocTypesAllowTest(ExternalDocTypesAllowBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_access = self.bloom.bloom_require_external_doc_type(
            self.parameters.EXTERNAL_GRANTED, self.parameters.EXTERNAL_GRANTED_TYPE
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExternalDocTypesAllowTest().run()
