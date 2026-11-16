"""
* @file     ${tests/sec/campaigns_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which campaigns an external reader gets and what a synchronised result changes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the campaigns an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class CampaignsExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_lists_only_the_customer_campaign(self):
        self.print_variables({"status": self.listed.status, "body": self.listed.body})
        self.assertEqual(
            (self.listed.status, [item["campaign_id"] for item in self.listed.body["items"]]),
            (self.parameters.STATUS_OK, [self.parameters.READER_VISIBLE_CAMPAIGN]),
            msg=self.parameters.MSG_READER_CAMPAIGN_LIST,
            abort_on_fail=False,
        )

    def bud_listed_campaign_carries_its_last_execution(self):
        self.assertEqual(
            (
                self.listed.body["items"][0]["total_items"],
                self.listed.body["items"][0]["last_execution_status"],
                self.listed.body["items"][0]["last_executed_at"][:19],
            ),
            self.parameters.READER_CAMPAIGN_EXECUTION,
            msg=self.parameters.MSG_READER_CAMPAIGN_LIST_EXECUTION,
            abort_on_fail=False,
        )

    def bud_internal_campaign_is_hidden_404(self):
        self.print_variables({"status": self.hidden.status, "body": self.hidden.body})
        self.assertEqual(
            self.hidden.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_CAMPAIGN_HIDDEN,
            abort_on_fail=False,
        )

    def bud_customer_campaign_opens_with_its_visibility(self):
        self.print_variables({"status": self.visible.status, "body": self.visible.body})
        self.assertEqual(
            (self.visible.status, self.visible.body["visibility"]),
            (self.parameters.STATUS_OK, self.parameters.CUSTOMER_VISIBILITY),
            msg=self.parameters.MSG_READER_CAMPAIGN_SHOWN,
            abort_on_fail=False,
        )

    def bud_opened_campaign_carries_its_last_execution(self):
        self.assertEqual(
            (
                self.visible.body["total_items"],
                self.visible.body["last_execution_status"],
                self.visible.body["last_executed_at"][:19],
            ),
            self.parameters.READER_CAMPAIGN_EXECUTION,
            msg=self.parameters.MSG_READER_CAMPAIGN_EXECUTION,
            abort_on_fail=False,
        )

    def bud_opened_campaign_holds_only_the_customer_test_case(self):
        self.assertEqual(
            [item["test_case"]["tc_id"] for item in self.visible.body["items"]],
            [self.parameters.READER_CUSTOMER_TC],
            msg=self.parameters.MSG_READER_CAMPAIGN_ITEMS,
            abort_on_fail=False,
        )

    def bud_opened_campaign_names_only_the_customer_suite(self):
        self.assertEqual(
            [scope["suite"]["suite_id"] for scope in self.visible.body["suite_scopes"]],
            [self.parameters.READER_VISIBLE_SUITE],
            msg=self.parameters.MSG_READER_CAMPAIGN_SUITES,
            abort_on_fail=False,
        )

    def bud_synchronising_a_result_is_answered_200(self):
        self.print_variables({"status": self.synced.status, "body": self.synced.body})
        self.assertEqual(
            self.synced.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_READER_SYNC,
            abort_on_fail=False,
        )

    def bud_synchronised_result_gives_the_campaign_no_bud_run(self):
        self.print_variables({"status": self.after_sync.status, "body": self.after_sync.body})
        self.assertEqual(
            (
                self.after_sync.status,
                self.after_sync.body["bud_run_id"],
                self.after_sync.body["bud_run_url"],
            ),
            (self.parameters.STATUS_OK, None, None),
            msg=self.parameters.MSG_READER_SYNC_NO_RUN,
            abort_on_fail=False,
        )

    def bud_campaign_item_carries_the_synchronised_result(self):
        item = self.after_sync.body["items"][0]
        self.assertEqual(
            (item["result"], item["executed_at"][:19]),
            (self.parameters.EXPORT_PASSED, self.parameters.READER_SYNC_AT),
            msg=self.parameters.MSG_READER_SYNC_ITEM,
            abort_on_fail=False,
        )
