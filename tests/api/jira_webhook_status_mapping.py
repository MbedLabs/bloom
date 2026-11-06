"""
* @file     ${tests/api/jira_webhook_status_mapping.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which Jira statuses change the Bloom status of a defect.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests which Jira statuses change the Bloom status of a defect.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookStatusMappingBase(BloomTestCase):

    def bud_other_jira_status_keeps_the_bloom_status(self):
        self.bloom.bloom_set_defect_status(self.tc_env.defect_id, self.parameters.DEFECT_VERIFIED)
        self.bloom.bloom_post_jira_webhook(
            self.tc_in_review, delivery=self.parameters.DELIVERIES[0]
        )
        status = self.bloom.bloom_get_defect(self.tc_env.defect_id).status
        self.print_variables({"defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_VERIFIED,
            msg=self.parameters.MSG_OTHER_STATUS_KEEPS,
            abort_on_fail=False,
        )

    def bud_done_closes_the_defect(self):
        self.bloom.bloom_post_jira_webhook(self.tc_done, delivery=self.parameters.DELIVERIES[1])
        status = self.bloom.bloom_get_defect(self.tc_env.defect_id).status
        self.print_variables({"defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_DONE_CLOSES,
            abort_on_fail=False,
        )

    def bud_leaving_done_reopens_a_defect_jira_closed(self):
        self.bloom.bloom_post_jira_webhook(
            self.tc_in_review, delivery=self.parameters.DELIVERIES[2]
        )
        status = self.bloom.bloom_get_defect(self.tc_env.defect_id).status
        self.print_variables({"defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_OPEN,
            msg=self.parameters.MSG_REOPEN_OPENS,
            abort_on_fail=False,
        )

    def bud_defect_closed_in_bloom_stays_closed(self):
        self.bloom.bloom_set_defect_status(self.tc_env.defect_id, self.parameters.DEFECT_CLOSED)
        self.bloom.bloom_post_jira_webhook(
            self.tc_in_review_renamed, delivery=self.parameters.DELIVERIES[3]
        )
        status = self.bloom.bloom_get_defect(self.tc_env.defect_id).status
        self.print_variables({"defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_BLOOM_CLOSE_KEPT,
            abort_on_fail=False,
        )
