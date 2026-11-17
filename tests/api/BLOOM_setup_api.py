"""
* @file     ${tests/api/BLOOM_setup_api.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An instance without users is set up once with an administrator, with or without mail.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the setup routes on the full application; each step starts from a database without users.
"""

from tests.api.setup_api import SetupApiBase


class SetupApiTest(SetupApiBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    SetupApiTest().run()
