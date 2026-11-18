"""
* @file     ${tests/logic/BLOOM_related_docs_filter.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Documents can be filtered to the artefacts sharing a relationship with one document.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the filter on a project with an anchor requirement, an unrelated one and two linked test cases.
"""

from tests.logic.related_docs_filter import RelatedDocsFilterBase


class RelatedDocsFilterTest(RelatedDocsFilterBase):

    def setUpClass(self):
        super().setUpClass()
        self.docs = self.bloom.bloom_seed_related_docs()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RelatedDocsFilterTest().run()
