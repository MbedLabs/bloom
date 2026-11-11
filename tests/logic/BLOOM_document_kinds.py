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
        self.tc_normalized = {
            value: self.bloom.bloom_normalize_document_kind(value)
            for value, _ in self.parameters.DOC_KIND_LEGACY
        }
        self.tc_required = {
            value: self.bloom.bloom_require_document_kind(value)
            for value in self.parameters.DOC_KIND_ACCEPTED + self.parameters.DOC_KIND_REFUSED
        }
        self.tc_slugs = {
            slug: self.bloom.bloom_document_kind_from_slug(slug)
            for slug, _ in self.parameters.DOC_KIND_SLUGS
        }
        self.tc_links = self.bloom.bloom_count_links(
            self.parameters.DOC_KIND_LINK_PROJECT,
            self.parameters.DOC_KIND_LINK_TYPE,
            self.parameters.DOC_KIND_INCOMING,
            self.parameters.DOC_KIND_OUTGOING,
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentKindsTest().run()
