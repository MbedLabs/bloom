"""
* @file     ${tests/api/jira_webhook_inbound_off.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a mapped project that does not create defects from Jira.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests a mapped project that does not create defects from Jira.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookInboundOffBase(BloomTestCase):

    def bud_unmatched_issue_is_not_found(self):
        self.print_variables({"status": self.tc_response.status_code})
        self.assertEqual(
            self.tc_response.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_INBOUND_OFF,
            abort_on_fail=False,
        )
