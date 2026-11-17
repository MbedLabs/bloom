"""
* @file     ${tests/api/jira_webhook_deleted_issue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a Jira deletion of linked issues.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests a Jira deletion of linked issues.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookDeletedIssueBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_deleted_issue_keeps_its_defect(self):
        defect_gone = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER),
            event=self.parameters.ISSUE_DELETED,
        )
        response = self.bloom.bloom_post_jira_webhook(
            defect_gone, delivery=self.parameters.DELIVERIES[7]
        )
        defect = self.bloom.bloom_get_defect(self.env.defect_id)
        found = (response.json().get("status"), defect.external_issue_state, defect.title)
        self.print_variables({"answer, state, title": found})
        self.assertEqual(
            found,
            (
                self.parameters.ANSWER_PROCESSED,
                self.parameters.REMOVED_STATE,
                self.parameters.OLD_TITLE,
            ),
            msg=self.parameters.MSG_DELETED_KEPT,
            abort_on_fail=False,
        )

    def bud_deleted_issue_marks_its_change_request(self):
        change_gone = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.CHANGE_NUMBER),
            event=self.parameters.ISSUE_DELETED,
        )
        self.bloom.bloom_post_jira_webhook(change_gone, delivery=self.parameters.DELIVERIES[8])
        state = self.bloom.bloom_get_change(self.env.change_id).external_issue_state
        self.print_variables({"change request state": state})
        self.assertEqual(
            state,
            self.parameters.REMOVED_STATE,
            msg=self.parameters.MSG_DELETED_CHANGE,
            abort_on_fail=False,
        )
