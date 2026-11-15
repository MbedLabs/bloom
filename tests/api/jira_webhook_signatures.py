"""
* @file     ${tests/api/jira_webhook_signatures.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the signature and delivery checks of the Jira webhook.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests the signature and delivery checks of the Jira webhook.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookSignaturesBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_missing_signature_is_refused(self):
        response = self.bloom.bloom_post_jira_webhook(
            self.tc_body, delivery=self.parameters.DELIVERIES[0], signed=False
        )
        self.print_variables({"status": response.status_code})
        self.assertEqual(
            response.status_code,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_MISSING_SIGNATURE,
            abort_on_fail=False,
        )

    def bud_wrong_signature_is_refused(self):
        response = self.bloom.bloom_post_jira_webhook(
            self.tc_body,
            signature=self.parameters.FORGED_SIGNATURE,
            delivery=self.parameters.DELIVERIES[1],
        )
        self.print_variables({"status": response.status_code})
        self.assertEqual(
            response.status_code,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_WRONG_SIGNATURE,
            abort_on_fail=False,
        )

    def bud_signature_of_another_body_is_refused(self):
        other = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.UNLINKED_NUMBER)
        )
        response = self.bloom.bloom_post_jira_webhook(
            self.tc_body,
            signature=self.bloom.bloom_sign(other),
            delivery=self.parameters.DELIVERIES[2],
        )
        self.print_variables({"status": response.status_code})
        self.assertEqual(
            response.status_code,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_FOREIGN_SIGNATURE,
            abort_on_fail=False,
        )

    def bud_missing_delivery_identifier_is_refused(self):
        response = self.bloom.bloom_post_jira_webhook(self.tc_body)
        self.print_variables({"status": response.status_code})
        self.assertEqual(
            response.status_code,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_MISSING_DELIVERY,
            abort_on_fail=False,
        )
