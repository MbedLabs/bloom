"""
* @file     ${tests/api/jira_webhook_issue_filter.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which Jira issues a mapped project takes in.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests which Jira issues a mapped project takes in.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookIssueFilterBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_task_is_ignored(self):
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.FILTER_NUMBERS[0]),
            event=self.parameters.ISSUE_CREATED,
            status={
                "name": self.parameters.JIRA_TO_DO,
                "statusCategory": {"key": self.parameters.JIRA_NEW},
            },
            issuetype={"name": self.parameters.TASK},
        )
        task = self.bloom.bloom_post_jira_webhook(body, delivery=self.parameters.DELIVERIES[1])
        self.print_variables({"answer": task.json()})
        self.assertEqual(
            task.json().get("status"),
            self.parameters.ANSWER_IGNORED,
            msg=self.parameters.MSG_TASK_IGNORED,
            abort_on_fail=False,
        )

    def bud_unlabelled_issue_is_ignored(self):
        self.bloom.bloom_update_setting(self.env.setting_id, jira_label=self.parameters.LABEL)
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.FILTER_NUMBERS[1]),
            event=self.parameters.ISSUE_CREATED,
            status={
                "name": self.parameters.JIRA_TO_DO,
                "statusCategory": {"key": self.parameters.JIRA_NEW},
            },
        )
        unlabelled = self.bloom.bloom_post_jira_webhook(
            body, delivery=self.parameters.DELIVERIES[2]
        )
        self.print_variables({"answer": unlabelled.json()})
        self.assertEqual(
            unlabelled.json(),
            self.parameters.NOT_TAKEN_IN,
            msg=self.parameters.MSG_UNLABELLED_IGNORED,
            abort_on_fail=False,
        )

    def bud_labelled_issue_creates_a_defect_without_reporter(self):
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.FILTER_NUMBERS[2]),
            event=self.parameters.ISSUE_CREATED,
            status={
                "name": self.parameters.JIRA_TO_DO,
                "statusCategory": {"key": self.parameters.JIRA_NEW},
            },
            labels=[self.parameters.LABEL],
        )
        labelled = self.bloom.bloom_post_jira_webhook(body, delivery=self.parameters.DELIVERIES[3])
        created = self.bloom.bloom_list_defects_linked_to(self.parameters.FILTER_NUMBERS[2])
        found = (labelled.json().get("status"), [d.reporter_id for d in created])
        self.print_variables({"answer, reporters": found})
        self.assertEqual(
            found,
            (self.parameters.ANSWER_CREATED, [None]),
            msg=self.parameters.MSG_LABELLED_CREATED,
            abort_on_fail=False,
        )

    def bud_deletion_of_an_unknown_issue_is_ignored(self):
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.FILTER_NUMBERS[3]),
            event=self.parameters.ISSUE_DELETED,
            status={
                "name": self.parameters.JIRA_TO_DO,
                "statusCategory": {"key": self.parameters.JIRA_NEW},
            },
        )
        gone = self.bloom.bloom_post_jira_webhook(body, delivery=self.parameters.DELIVERIES[4])
        self.print_variables({"answer": gone.json()})
        self.assertEqual(
            gone.json().get("status"),
            self.parameters.ANSWER_IGNORED,
            msg=self.parameters.MSG_UNKNOWN_DELETE_IGNORED,
            abort_on_fail=False,
        )
