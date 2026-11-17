"""
* @file     ${tests/api/BLOOM_visions_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A Vision is its own document kind with built-in access, link rules and review.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests visions on the full application with the built-in policies and groups; each step uses its own project.
"""

from tests.api.visions_http import VisionsHttpBase


class VisionsHttpTest(VisionsHttpBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.bloom.bloom_seed_default_catalogue()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    VisionsHttpTest().run()
