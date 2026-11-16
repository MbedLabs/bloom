"""
* @file     ${tests/logic/BLOOM_search.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The global search finds records by id and title within the projects and document types the user may read.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the search on two projects holding login records, as administrator, member and external reader.
"""

from tests.logic.search import SearchBase


class SearchTest(SearchBase):

    def setUpClass(self):
        super().setUpClass()
        self.records = self.bloom.bloom_seed_search_records()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    SearchTest().run()
