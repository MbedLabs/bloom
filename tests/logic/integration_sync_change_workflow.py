"""
* @file     ${tests/logic/integration_sync_change_workflow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the Jira sync of change requests in and outside their workflow.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the change request workflow.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncChangeWorkflowBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_run_succeeds_at_now(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.print_variables({"error": setting.sync_error, "synced at": setting.synced_at})
        self.assertEqual(
            (setting.sync_error, setting.synced_at),
            (None, self.parameters.NOW),
            msg=self.parameters.MSG_WORKFLOW_RUN_OK,
            abort_on_fail=False,
        )

    def bud_approved_change_request_keeps_its_status(self):
        change = self.bloom.bloom_get_change(self.tc_approved_id)
        self.print_variables({"status": change.status, "issue state": change.external_issue_state})
        self.assertEqual(
            (change.status, change.external_issue_state),
            (self.parameters.CHANGE_APPROVED, self.parameters.JIRA_DONE),
            msg=self.parameters.MSG_APPROVED_KEPT,
            abort_on_fail=False,
        )

    def bud_submitted_change_request_with_a_resolved_issue_is_closed(self):
        status = self.bloom.bloom_get_change(self.tc_submitted_id).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_SUBMITTED_CLOSED,
            abort_on_fail=False,
        )
