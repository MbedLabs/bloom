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
        listed = self.bloom.bloom_api_list_test_cases(self.reader.headers, self.reader.project_id)
        self.print_variables({"status": listed.status, "body": listed.body})
        self.assertEqual(
            (listed.status, [item["tc_id"] for item in listed.body["items"]]),
            (self.parameters.STATUS_OK, [self.parameters.READER_CUSTOMER_TC]),
            msg=self.parameters.MSG_READER_TC_LIST,
            abort_on_fail=False,
        )

    def bud_test_case_carries_its_visibility(self):
        read = self.bloom.bloom_api_get_test_case(self.admin, self.customer)
        self.print_variables({"status": read.status, "body": read.body})
        self.assertEqual(
            (read.status, read.body["visibility"]),
            (self.parameters.STATUS_OK, self.parameters.CUSTOMER_VISIBILITY),
            msg=self.parameters.MSG_READER_TC_VISIBILITY,
            abort_on_fail=False,
        )
