"""
* @file     ${tests/api/BLOOM_links_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A link is created only with a role its two kinds allow, and a link stored under an old kind code is still found.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the link routes on the full application as administrator.
"""

from tests.api.links_http import LinksHttpBase


class LinksHttpTest(LinksHttpBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    LinksHttpTest().run()
