"""
* @file     ${tests/api/jira_webhook_closes_defect.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a signed webhook that closes a linked defect.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests a signed webhook that closes a linked defect.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookClosesDefectBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_signed_update_answers_for_the_defect(self):
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
        )
        response = self.bloom.bloom_post_jira_webhook(body, delivery=self.parameters.DELIVERIES[0])
        found = (response.status_code, response.json().get("target"))
        self.print_variables({"status, target": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.parameters.TARGET_DEFECT),
            msg=self.parameters.MSG_DEFECT_TARGET,
            abort_on_fail=False,
        )

    def bud_linked_defect_is_closed(self):
        status = self.bloom.bloom_get_defect(self.env.defect_id).status
        self.print_variables({"defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_DEFECT_CLOSED_BY_WEBHOOK,
            abort_on_fail=False,
        )
