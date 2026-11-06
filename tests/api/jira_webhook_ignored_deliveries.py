"""
* @file     ${tests/api/jira_webhook_ignored_deliveries.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests signed deliveries the webhook does not apply.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests signed deliveries the webhook does not apply.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookIgnoredDeliveriesBase(BloomTestCase):

    def bud_unlinked_issue_is_not_found(self):
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.UNLINKED_NUMBER)
        )
        response = self.bloom.bloom_post_jira_webhook(body, delivery=self.parameters.DELIVERIES[5])
        self.print_variables({"status": response.status_code})
        self.assertEqual(
            response.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_UNLINKED_404,
            abort_on_fail=False,
        )

    def bud_non_issue_event_is_ignored(self):
        response = self.bloom.bloom_post_jira_webhook(
            self.bloom.bloom_jira_event_body(self.parameters.WORKLOG_UPDATED),
            delivery=self.parameters.DELIVERIES[6],
        )
        found = (response.status_code, response.json().get("status"))
        self.print_variables({"status, answer": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.parameters.ANSWER_IGNORED),
            msg=self.parameters.MSG_NON_ISSUE_IGNORED,
            abort_on_fail=False,
        )

    def bud_malformed_issue_key_is_ignored(self):
        response = self.bloom.bloom_post_jira_webhook(
            self.bloom.bloom_jira_webhook_body(self.parameters.MALFORMED_KEY),
            delivery=self.parameters.DELIVERIES[7],
        )
        found = (response.status_code, response.json().get("status"))
        self.print_variables({"status, answer": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.parameters.ANSWER_IGNORED),
            msg=self.parameters.MSG_MALFORMED_IGNORED,
            abort_on_fail=False,
        )
