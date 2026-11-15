"""
* @file     ${tests/logic/BLOOM_external_doc_types_allowlist.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external member's document types are exactly the types their term grants.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the allowlist of a term granting two document types.
"""

from tests.logic.external_doc_types_allowlist import ExternalDocTypesAllowlistBase


class ExternalDocTypesAllowlistTest(ExternalDocTypesAllowlistBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_allowed = self.bloom.bloom_external_doc_types(self.parameters.EXTERNAL_ALLOWLIST)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExternalDocTypesAllowlistTest().run()
