"""
* @file     ${tests/api/BLOOM_requirements_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A requirement is created, listed, read, changed and deleted over HTTP, and a test case keeps its editor body.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the routes on the full application as administrator.
"""

from tests.api.requirements_http import RequirementsHttpBase


class RequirementsHttpTest(RequirementsHttpBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementsHttpTest().run()
