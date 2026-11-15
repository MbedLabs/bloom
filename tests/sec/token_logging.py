"""
* @file     ${tests/sec/token_logging.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that one-time tokens stay out of the application log.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the token logging check.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TokenLoggingBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_request_reaches_the_log(self):
        self.print_variables({"path": self.parameters.INVITE_INFO_PATH, "logs": self.tc_logs})
        self.assertIn(
            self.parameters.INVITE_INFO_PATH,
            self.tc_logs,
            msg=self.parameters.MSG_TOKEN_REQUEST_LOGGED,
            abort_on_fail=False,
        )

    def bud_token_stays_out_of_the_log(self):
        self.print_variables({"token": self.parameters.ONE_TIME_TOKEN})
        self.assertNotIn(
            self.parameters.ONE_TIME_TOKEN,
            self.tc_logs,
            msg=self.parameters.MSG_TOKEN_NOT_LOGGED,
            abort_on_fail=False,
        )
