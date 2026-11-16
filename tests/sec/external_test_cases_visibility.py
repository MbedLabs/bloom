"""
* @file     ${tests/sec/external_test_cases_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which test cases an external reader lists.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the test cases an external reader lists.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ExternalTestCasesVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_lists_only_the_customer_test_case(self):
        self.print_variables({"status": self.tc_listed.status, "body": self.tc_listed.body})
        self.assertEqual(
            (self.tc_listed.status, [item["tc_id"] for item in self.tc_listed.body["items"]]),
            (self.parameters.STATUS_OK, [self.parameters.READER_CUSTOMER_TC]),
            msg=self.parameters.MSG_READER_TC_LIST,
            abort_on_fail=False,
        )

    def bud_test_case_carries_its_visibility(self):
        self.print_variables({"status": self.tc_read.status, "body": self.tc_read.body})
        self.assertEqual(
            (self.tc_read.status, self.tc_read.body["visibility"]),
            (self.parameters.STATUS_OK, self.parameters.CUSTOMER_VISIBILITY),
            msg=self.parameters.MSG_READER_TC_VISIBILITY,
            abort_on_fail=False,
        )
