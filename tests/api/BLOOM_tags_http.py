"""
* @file     ${tests/api/BLOOM_tags_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The tags a policy ticks per document type decide what a user sees, creates and changes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests tags on the full application; each step uses its own project, tags and users.
"""

from tests.api.tags_http import TagsHttpBase


class TagsHttpTest(TagsHttpBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TagsHttpTest().run()
