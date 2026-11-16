"""
* @file     ${tests/sec/external_visibility_direct_apis.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what a customer artefact shows an external reader of the artefacts linked to it.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the linked artefacts an external reader sees.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ExternalVisibilityDirectApisBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_requirement_shows_only_its_customer_neighbours(self):
        self.print_variables(
            {"status": self.tc_requirement.status, "body": self.tc_requirement.body}
        )
        body = self.tc_requirement.body
        self.assertEqual(
            (
                self.tc_requirement.status,
                [tc["tc_id"] for tc in body["linked_test_cases"]],
                [link["test_case"]["tc_id"] for link in body["verified_by"]],
                [suite["suite_id"] for suite in body["suite_backlinks"]],
                [campaign["campaign_id"] for campaign in body["campaign_backlinks"]],
            ),
            (
                self.parameters.STATUS_OK,
                [self.parameters.READER_CUSTOMER_TC],
                [self.parameters.READER_CUSTOMER_TC],
                [self.parameters.READER_VISIBLE_SUITE],
                [self.parameters.READER_VISIBLE_CAMPAIGN],
            ),
            msg=self.parameters.MSG_DIRECT_REQUIREMENT,
            abort_on_fail=False,
        )

    def bud_test_case_shows_only_its_customer_neighbours(self):
        self.print_variables({"status": self.tc_test_case.status, "body": self.tc_test_case.body})
        body = self.tc_test_case.body
        self.assertEqual(
            (
                self.tc_test_case.status,
                [req["req_id"] for req in body["linked_requirements"]],
                [link["requirement"]["req_id"] for link in body["verifies"]],
                [suite["suite_id"] for suite in body["suite_memberships"]],
                [campaign["campaign_id"] for campaign in body["campaign_memberships"]],
            ),
            (
                self.parameters.STATUS_OK,
                [self.parameters.READER_CUSTOMER_REQ],
                [self.parameters.READER_CUSTOMER_REQ],
                [self.parameters.READER_VISIBLE_SUITE],
                [self.parameters.READER_VISIBLE_CAMPAIGN],
            ),
            msg=self.parameters.MSG_DIRECT_TEST_CASE,
            abort_on_fail=False,
        )

    def bud_campaign_shows_only_its_customer_neighbours(self):
        self.print_variables({"status": self.tc_campaign.status, "body": self.tc_campaign.body})
        body = self.tc_campaign.body
        self.assertEqual(
            (
                self.tc_campaign.status,
                [item["test_case"]["tc_id"] for item in body["items"]],
                [req["req_id"] for req in body["items"][0]["test_case"]["linked_requirements"]],
                [req["req_id"] for req in body["related_requirements"]],
            ),
            (
                self.parameters.STATUS_OK,
                [self.parameters.READER_CUSTOMER_TC],
                [self.parameters.READER_CUSTOMER_REQ],
                [self.parameters.READER_CUSTOMER_REQ],
            ),
            msg=self.parameters.MSG_DIRECT_CAMPAIGN,
            abort_on_fail=False,
        )
