"""
* @file     ${tests/sec/BLOOM_cli_auth_security.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The CLI sign-in refuses redirect abuse, replay and revoked identities, and honours code sign-in turned off.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the CLI sign-in API; each step creates its own sign-in account, second account and project.
"""

from tests.sec.cli_auth_security import CliAuthSecurityBase


class CliAuthSecurityTest(CliAuthSecurityBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthSecurityTest().run()
