"""
* @file     ${tests/logic/response_timestamps.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that every timestamp an API response carries is marked as UTC.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the response timestamps.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ResponseTimestampsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_scan_finds_the_response_models(self):
        api_models = [
            name for name in self.tc_models if name.startswith(self.parameters.RESPONSE_API_PREFIX)
        ]
        self.print_variables({"models": len(self.tc_models), "in app.api": len(api_models)})
        self.assertGreater(
            len(self.tc_models),
            self.parameters.RESPONSE_MIN_MODELS,
            msg=self.parameters.MSG_RESPONSE_SCAN_COUNT,
            abort_on_fail=False,
        )
        self.assertTrue(
            bool(api_models),
            msg=self.parameters.MSG_RESPONSE_SCAN_API,
            expected=f"a model named {self.parameters.RESPONSE_API_PREFIX}*",
            actual=api_models[:3],
            abort_on_fail=False,
        )

    def bud_every_response_timestamp_is_utc(self):
        self.print_variables({"unmarked": self.tc_unmarked})
        self.assertEqual(
            self.tc_unmarked,
            self.parameters.RESPONSE_NONE_UNMARKED,
            msg=self.parameters.MSG_RESPONSE_UTC,
            abort_on_fail=False,
        )
