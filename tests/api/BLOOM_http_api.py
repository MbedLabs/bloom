"""
* @file     ${tests/api/BLOOM_http_api.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The probes, root and docs switch answer as deployed; signing in opens the API.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the full app in-process with an admin account.
"""

from tests.api.http_api import HttpApiBase


class HttpApiTest(HttpApiBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    HttpApiTest().run()
