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
        standard = self.bloom.bloom_sign_in_with_token(
            self.bloom.bloom_forge_token(
                self.user_id, self.parameters.TOKEN_STANDARD, self.parameters.TOKEN_VALID_MINUTES
            )
        )
        self.print_variables({"user": self.user_id, "answer": standard})
        self.assertEqual(
            standard,
            (self.user_id, None),
            msg=self.parameters.MSG_TOKEN_STANDARD,
            abort_on_fail=False,
        )

    def bud_issued_token_signs_in(self):
        issued = self.bloom.bloom_sign_in_with_token(self.bloom.bloom_issue_token(self.user_id))
        self.print_variables({"user": self.user_id, "answer": issued})
        self.assertEqual(
            issued,
            (self.user_id, None),
            msg=self.parameters.MSG_TOKEN_ISSUED,
            abort_on_fail=False,
        )

    @parameterized(params.TOKEN_REFUSAL_CASES)
    def bud_expired_or_other_algorithm_is_refused(self, index):
        algorithm, minutes = self.parameters.TOKEN_REFUSALS[index]
        answer = self.bloom.bloom_sign_in_with_token(
            self.bloom.bloom_forge_token(self.user_id, algorithm, minutes)
        )
        self.print_variables({"algorithm": algorithm, "minutes": minutes, "answer": answer})
        self.assertEqual(
            answer,
            (None, self.parameters.STATUS_UNAUTHORIZED),
            msg=self.parameters.MSG_TOKEN_REFUSED,
            abort_on_fail=False,
        )
