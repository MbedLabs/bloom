"""
* @file     ${tests/logic/BLOOM_invites.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    One-time user tokens hash deterministically, keep their purposes and expire later.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the token hash, the purpose values and a new invite token.
"""

from tests.logic.invites import InvitesBase


class InvitesTest(InvitesBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_hash = self.bloom.bloom_hash_token(self.parameters.INVITE_TOKEN)
        self.tc_other_hash = self.bloom.bloom_hash_token(self.parameters.INVITE_OTHER_TOKEN)
        self.tc_purposes = self.bloom.bloom_token_purpose_values()
        self.tc_token = self.bloom.bloom_new_invite_token(self.parameters.INVITE_VALID_HOURS)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    InvitesTest().run()
