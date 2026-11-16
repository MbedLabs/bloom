"""
* @file     ${tests/logic/access_token_format.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which access tokens sign a user in.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the access token format.
"""

from budtestlibrary import parameterized

import tests.parameters as params
from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class AccessTokenFormatBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_standard_hs256_token_signs_in(self):
        self.print_variables({"user": self.user_id, "answer": self.standard})
        self.assertEqual(
            self.standard,
            (self.user_id, None),
            msg=self.parameters.MSG_TOKEN_STANDARD,
            abort_on_fail=False,
        )

    def bud_issued_token_signs_in(self):
        self.print_variables({"user": self.user_id, "answer": self.issued})
        self.assertEqual(
            self.issued,
            (self.user_id, None),
            msg=self.parameters.MSG_TOKEN_ISSUED,
            abort_on_fail=False,
        )

    @parameterized(params.TOKEN_REFUSAL_CASES)
    def bud_expired_or_other_algorithm_is_refused(self, index):
        algorithm, minutes = self.parameters.TOKEN_REFUSALS[index]
        answer = self.refusals[index]
        self.print_variables({"algorithm": algorithm, "minutes": minutes, "answer": answer})
        self.assertEqual(
            answer,
            (None, self.parameters.STATUS_UNAUTHORIZED),
            msg=self.parameters.MSG_TOKEN_REFUSED,
            abort_on_fail=False,
        )
