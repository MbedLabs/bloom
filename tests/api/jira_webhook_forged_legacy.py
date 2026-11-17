"""
* @file     ${tests/api/jira_webhook_forged_legacy.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a forged delivery against a submitted change request.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests a forged delivery against a submitted change request.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookForgedLegacyBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_forged_delivery_is_refused_and_changes_nothing(self):
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.CHANGE_NUMBER)
        )
        response = self.bloom.bloom_post_jira_webhook(
            body, signature=self.parameters.FORGED_SIGNATURE, delivery=self.parameters.DELIVERIES[2]
        )
        status = self.bloom.bloom_get_change(self.env.change_id).status
        found = (response.status_code, status)
        self.print_variables({"answer, status": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_FORBIDDEN, self.parameters.CHANGE_SUBMITTED),
            msg=self.parameters.MSG_FORGED_LEGACY,
            abort_on_fail=False,
        )
