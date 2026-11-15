"""
* @file     ${tests/logic/BLOOM_next_doc_id.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The create screen previews the next free document id of the project and type.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests the next id over empty, taken, gapped and mixed id lists.
"""

from tests.logic.next_doc_id import NextDocIdBase


class NextDocIdTest(NextDocIdBase):

    def setUpClass(self):
        super().setUpClass()
        prefix = self.parameters.NEXT_ID_PREFIX
        kind = self.parameters.NEXT_ID_TYPE
        self.tc_empty = self.bloom.bloom_compute_next_id([], prefix, kind)
        self.tc_after_taken = self.bloom.bloom_compute_next_id(
            self.parameters.NEXT_ID_TAKEN_IDS, prefix, kind
        )
        self.tc_after_gap = self.bloom.bloom_compute_next_id(
            self.parameters.NEXT_ID_GAP_IDS, prefix, kind
        )
        self.tc_among_others = self.bloom.bloom_compute_next_id(
            self.parameters.NEXT_ID_MIXED_IDS, prefix, kind
        )
        self.tc_unsupported = self.bloom.bloom_compute_next_id(
            [], prefix, self.parameters.NEXT_ID_UNSUPPORTED_TYPE
        )
        self.tc_routes = self.bloom.bloom_list_docs_routes()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    NextDocIdTest().run()
