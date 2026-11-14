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
        self.tc_user_id = self.bloom.bloom_add_user(
            self.parameters.TOKEN_EMAIL, self.bloom.bloom_maintainer_role()
        )
        self.tc_standard = self.bloom.bloom_sign_in_with_token(
            self.bloom.bloom_forge_token(
                self.tc_user_id, self.parameters.TOKEN_STANDARD, self.parameters.TOKEN_VALID_MINUTES
            )
        )
        self.tc_issued = self.bloom.bloom_sign_in_with_token(
            self.bloom.bloom_issue_token(self.tc_user_id)
        )
        self.tc_refusals = [
            self.bloom.bloom_sign_in_with_token(
                self.bloom.bloom_forge_token(self.tc_user_id, algorithm, minutes)
            )
            for algorithm, minutes in self.parameters.TOKEN_REFUSALS
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AccessTokenFormatTest().run()
