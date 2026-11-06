"""
* @file     ${tests/api/jira_webhook_change_workflow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests Jira closures outside a change request's workflow.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of Jira closures outside the workflow.
"""

from budtestlibrary import parameterized

import tests.parameters as params
from tests.bloom_test_base import BloomTestCase


class JiraWebhookChangeWorkflowBase(BloomTestCase):

    @parameterized(params.CHANGE_WORKFLOW_CASES)
    def bud_closure_outside_the_workflow_is_refused(self, index):
        response, status = self.tc_results[index]
        expected = self.parameters.CHANGE_WORKFLOW_STATUSES[index]
        self.print_variables(
            {"workflow status": expected, "answer": response.status_code, "status after": status}
        )
        self.assertEqual(
            (response.status_code, status),
            (self.parameters.STATUS_CONFLICT, expected),
            msg=self.parameters.MSG_WORKFLOW_CONFLICT,
            abort_on_fail=False,
        )
