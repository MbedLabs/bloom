"""
* @file     ${tests/api/BLOOM_public_id_paths.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Suites and campaigns are addressed by their public ID in the API; a database ID is a 404.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the suite and campaign routes on the full application; each step uses its own project.
"""

from tests.api.public_id_paths import PublicIdPathsBase


class PublicIdPathsTest(PublicIdPathsBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    PublicIdPathsTest().run()
