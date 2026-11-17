"""
* @file     ${tests/api/jira_webhook_replay.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that a delivery applies once.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests that a delivery applies once.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraWebhookReplayBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_replay_answers_duplicate(self):
        body = self.bloom.bloom_jira_webhook_body(
            self.bloom.bloom_jira_key(self.parameters.LINKED_NUMBER)
        )
        replay = self.bloom.bloom_post_jira_webhook(body, delivery=self.parameters.DELIVERIES[4])
        self.print_variables({"replay": replay.json()})
        self.assertEqual(
            replay.json().get("status"),
            self.parameters.ANSWER_DUPLICATE,
            msg=self.parameters.MSG_REPLAY_DUPLICATE,
            abort_on_fail=False,
        )

    def bud_replay_changes_nothing(self):
        status = self.bloom.bloom_get_defect(self.env.defect_id).status
        self.print_variables({"defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_OPEN,
            msg=self.parameters.MSG_REPLAY_NO_CHANGE,
            abort_on_fail=False,
        )
