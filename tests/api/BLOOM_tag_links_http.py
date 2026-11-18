"""
* @file     ${tests/api/BLOOM_tag_links_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A tag written in a document body becomes a references link.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests tags in requirement, specification and test case bodies on the full application; each step uses its own project.
"""

from tests.api.tag_links_http import TagLinksHttpBase


class TagLinksHttpTest(TagLinksHttpBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TagLinksHttpTest().run()
