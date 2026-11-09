"""
* @file     ${tests/logic/integration_sync_removed_issues.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the Jira sync's check of linked issues for removal.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the removal check.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncRemovedIssuesBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_first_run_reads_the_lowest_linked_issue(self):
        self.print_variables({"reads": self.tc_first_reads})
        self.assertEqual(
            self.tc_first_reads,
            [self.tc_gone_key],
            msg=self.parameters.MSG_FIRST_READ,
            abort_on_fail=False,
        )

    def bud_gone_issue_marks_its_defect_removed(self):
        state = self.bloom.bloom_get_defect(self.tc_defect_id).external_issue_state
        self.print_variables({"defect issue state": state})
        self.assertEqual(
            state,
            self.parameters.REMOVED_STATE,
            msg=self.parameters.MSG_GONE_REMOVED,
            abort_on_fail=False,
        )

    def bud_cursor_stops_at_the_gone_issue(self):
        self.print_variables({"cursor, updated": self.tc_first_cursor})
        self.assertEqual(
            self.tc_first_cursor,
            (self.parameters.REMOVED_NUMBERS[0], 1),
            msg=self.parameters.MSG_CURSOR_FIRST,
            abort_on_fail=False,
        )

    def bud_defect_logs_its_removal(self):
        events = [e.payload_summary for e in self.bloom.bloom_list_defect_events()]
        self.print_variables({"defect events": events})
        self.assertEqual(
            events,
            [self.parameters.REMOVED_EVENT],
            msg=self.parameters.MSG_REMOVAL_LOGGED,
            abort_on_fail=False,
        )

    def bud_second_run_reads_the_next_linked_issue(self):
        self.print_variables({"reads": self.bloom.site.reads})
        self.assertEqual(
            self.bloom.site.reads,
            [self.tc_gone_key, self.tc_forbidden_key],
            msg=self.parameters.MSG_SECOND_READ,
            abort_on_fail=False,
        )

    def bud_forbidden_issue_leaves_the_change_request_unmarked(self):
        change = self.bloom.bloom_get_change(self.tc_change_id)
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        found = (change.external_issue_state, setting.sync_removal_cursor, setting.sync_error)
        self.print_variables({"issue state, cursor, error": found})
        self.assertEqual(
            found,
            (None, self.parameters.REMOVED_NUMBERS[1], None),
            msg=self.parameters.MSG_FORBIDDEN_UNMARKED,
            abort_on_fail=False,
        )
