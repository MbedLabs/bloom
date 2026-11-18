"""
* @file     ${tests/api/BLOOM_cli_auth.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Browser-approved CLI sessions keep the account's existing authority.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the CLI sign-in routes on the full application; each step starts from a new database with one reader.
"""

from tests.api.cli_auth import CliAuthBase


class CliAuthTest(CliAuthBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthTest().run()
