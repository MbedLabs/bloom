"""
* @file     ${tests/sec/external_test_suites_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which test suites an external reader gets and what they show.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the test suites an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ExternalTestSuitesVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_lists_only_the_customer_suite(self):
        self.print_variables({"status": self.listed.status, "body": self.listed.body})
        self.assertEqual(
            (self.listed.status, [item["suite_id"] for item in self.listed.body["items"]]),
            (self.parameters.STATUS_OK, [self.parameters.READER_VISIBLE_SUITE]),
            msg=self.parameters.MSG_READER_SUITE_LIST,
            abort_on_fail=False,
        )

    def bud_listed_suite_carries_its_last_execution(self):
        self.assertEqual(
            (
                self.listed.body["items"][0]["total_items"],
                self.listed.body["items"][0]["last_execution_status"],
                self.listed.body["items"][0]["last_executed_at"][:19],
                self.listed.body["items"][0]["last_bud_run_id"],
            ),
            self.parameters.READER_SUITE_EXECUTION,
            msg=self.parameters.MSG_READER_SUITE_LIST_EXECUTION,
            abort_on_fail=False,
        )

    def bud_internal_suite_is_hidden_404(self):
        hidden = self.bloom.bloom_api_get_test_suite(
            self.reader.headers, self.parameters.READER_HIDDEN_SUITE
        )
        self.print_variables({"status": hidden.status, "body": hidden.body})
        self.assertEqual(
            hidden.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_SUITE_HIDDEN,
            abort_on_fail=False,
        )

    def bud_customer_suite_opens_with_its_visibility(self):
        self.print_variables({"status": self.visible.status, "body": self.visible.body})
        self.assertEqual(
            (self.visible.status, self.visible.body["visibility"]),
            (self.parameters.STATUS_OK, self.parameters.CUSTOMER_VISIBILITY),
            msg=self.parameters.MSG_READER_SUITE_SHOWN,
            abort_on_fail=False,
        )

    def bud_opened_suite_carries_its_last_execution(self):
        self.assertEqual(
            (
                self.visible.body["total_items"],
                self.visible.body["last_execution_status"],
                self.visible.body["last_executed_at"][:19],
                self.visible.body["last_bud_run_id"],
            ),
            self.parameters.READER_SUITE_EXECUTION,
            msg=self.parameters.MSG_READER_SUITE_EXECUTION,
            abort_on_fail=False,
        )

    def bud_opened_suite_holds_only_the_customer_test_case(self):
        self.assertEqual(
            [item["test_case"]["tc_id"] for item in self.visible.body["items"]],
            [self.parameters.READER_CUSTOMER_TC],
            msg=self.parameters.MSG_READER_SUITE_ITEMS,
            abort_on_fail=False,
        )
