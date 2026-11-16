"""
* @file     ${tests/sec/test_suites_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which test suites an external reader gets and what they show.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the test suites an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TestSuitesExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_lists_only_the_customer_suite(self):
        self.print_variables({"status": self.tc_listed.status, "body": self.tc_listed.body})
        self.assertEqual(
            (self.tc_listed.status, [item["suite_id"] for item in self.tc_listed.body["items"]]),
            (self.parameters.STATUS_OK, [self.parameters.READER_VISIBLE_SUITE]),
            msg=self.parameters.MSG_READER_SUITE_LIST,
            abort_on_fail=False,
        )

    def bud_listed_suite_carries_its_last_execution(self):
        self.assertEqual(
            (
                self.tc_listed.body["items"][0]["total_items"],
                self.tc_listed.body["items"][0]["last_execution_status"],
                self.tc_listed.body["items"][0]["last_executed_at"][:19],
                self.tc_listed.body["items"][0]["last_bud_run_id"],
            ),
            self.parameters.READER_SUITE_EXECUTION,
            msg=self.parameters.MSG_READER_SUITE_LIST_EXECUTION,
            abort_on_fail=False,
        )

    def bud_internal_suite_is_hidden_404(self):
        self.print_variables({"status": self.tc_hidden.status, "body": self.tc_hidden.body})
        self.assertEqual(
            self.tc_hidden.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_SUITE_HIDDEN,
            abort_on_fail=False,
        )

    def bud_customer_suite_opens_with_its_visibility(self):
        self.print_variables({"status": self.tc_visible.status, "body": self.tc_visible.body})
        self.assertEqual(
            (self.tc_visible.status, self.tc_visible.body["visibility"]),
            (self.parameters.STATUS_OK, self.parameters.CUSTOMER_VISIBILITY),
            msg=self.parameters.MSG_READER_SUITE_SHOWN,
            abort_on_fail=False,
        )

    def bud_opened_suite_carries_its_last_execution(self):
        self.assertEqual(
            (
                self.tc_visible.body["total_items"],
                self.tc_visible.body["last_execution_status"],
                self.tc_visible.body["last_executed_at"][:19],
                self.tc_visible.body["last_bud_run_id"],
            ),
            self.parameters.READER_SUITE_EXECUTION,
            msg=self.parameters.MSG_READER_SUITE_EXECUTION,
            abort_on_fail=False,
        )

    def bud_opened_suite_holds_only_the_customer_test_case(self):
        self.assertEqual(
            [item["test_case"]["tc_id"] for item in self.tc_visible.body["items"]],
            [self.parameters.READER_CUSTOMER_TC],
            msg=self.parameters.MSG_READER_SUITE_ITEMS,
            abort_on_fail=False,
        )
