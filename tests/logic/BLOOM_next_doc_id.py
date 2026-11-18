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

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    NextDocIdTest().run()
