"""
* @file     ${tests/logic/invites.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the hashing, purposes and expiry of one-time user tokens.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the user tokens.
"""

from datetime import datetime

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class InvitesBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_token_hash_is_its_known_digest(self):
        self.print_variables({"token": self.parameters.INVITE_TOKEN, "hash": self.tc_hash})
        self.assertEqual(
            self.tc_hash,
            self.parameters.INVITE_TOKEN_HASH,
            msg=self.parameters.MSG_INVITE_HASH_KNOWN,
            abort_on_fail=False,
        )

    def bud_different_tokens_hash_differently(self):
        self.print_variables({"hash": self.tc_hash, "other": self.tc_other_hash})
        self.assertNotEqual(
            self.tc_hash,
            self.tc_other_hash,
            msg=self.parameters.MSG_INVITE_HASH_DIFFERS,
            abort_on_fail=False,
        )

    def bud_purposes_keep_their_values(self):
        for name, value in self.parameters.INVITE_PURPOSES.items():
            self.print_variables({"purpose": name, "value": self.tc_purposes.get(name)})
            self.assertEqual(
                self.tc_purposes.get(name),
                value,
                msg=self.parameters.MSG_INVITE_PURPOSE,
                abort_on_fail=False,
            )

    def bud_new_token_is_unused(self):
        self.print_variables({"used_at": self.tc_token.used_at})
        self.assertEqual(
            self.tc_token.used_at,
            self.parameters.INVITE_NOT_USED,
            msg=self.parameters.MSG_INVITE_UNUSED,
            abort_on_fail=False,
        )

    def bud_new_token_is_not_expired(self):
        now = datetime.utcnow()
        self.print_variables({"expires_at": self.tc_token.expires_at, "now": now})
        self.assertGreater(
            self.tc_token.expires_at,
            now,
            msg=self.parameters.MSG_INVITE_NOT_EXPIRED,
            abort_on_fail=False,
        )
