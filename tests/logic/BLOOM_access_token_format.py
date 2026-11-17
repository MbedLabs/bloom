"""
* @file     ${tests/logic/BLOOM_access_token_format.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A standard HS256 access token signs in; an expired one or another algorithm does not.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests forged and issued tokens of one user against the sign-in check.
"""

from tests.logic.access_token_format import AccessTokenFormatBase


class AccessTokenFormatTest(AccessTokenFormatBase):

    def setUpClass(self):
        super().setUpClass()
        self.user_id = self.bloom.bloom_add_user(
            self.parameters.TOKEN_EMAIL, self.bloom.bloom_maintainer_role()
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AccessTokenFormatTest().run()
