"""
* @file     ${tests/logic/integration_sync_now.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests Sync now on a Jira integration.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of Sync now.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncNowBase(BloomTestCase):

    def bud_sync_now_creates_updates_and_removes_in_one_call(self):
        found = (self.tc_result.created, self.tc_result.updated, self.tc_result.removed)
        self.print_variables({"created, updated, removed": found})
        self.assertEqual(
            found, (1, 1, 0), msg=self.parameters.MSG_SYNC_NOW_COUNTS, abort_on_fail=False
        )

    def bud_sync_now_checks_the_linked_issue(self):
        self.print_variables({"reads": self.bloom.site.reads})
        self.assertEqual(
            self.bloom.site.reads,
            [self.bloom.bloom_jira_key(self.parameters.CHANGE_NUMBER)],
            msg=self.parameters.MSG_SYNC_NOW_READ,
            abort_on_fail=False,
        )

    def bud_server_error_leaves_the_change_request_unmarked(self):
        state = self.bloom.bloom_get_change(self.tc_change_id).external_issue_state
        self.print_variables({"change request issue state": state})
        self.assertEqual(
            (state,), (None,), msg=self.parameters.MSG_SYNC_NOW_ERROR_UNMARKED, abort_on_fail=False
        )

    def bud_defect_created_by_sync_now_logs_it_was_pulled(self):
        created = self.bloom.bloom_list_defects_linked_to(self.parameters.NEW_NUMBER)
        ids = {defect.id for defect in created}
        events = [e.event_type for e in self.bloom.bloom_list_defect_events() if e.defect_id in ids]
        self.print_variables({"events of the created defect": events})
        self.assertEqual(
            events,
            [self.parameters.PULLED_EVENT],
            msg=self.parameters.MSG_SYNC_NOW_EVENT,
            abort_on_fail=False,
        )

    def bud_setting_records_the_run_cursor_and_counts(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        found = (
            setting.synced_at is not None,
            setting.sync_removal_cursor,
            setting.sync_created,
            setting.sync_updated,
        )
        self.print_variables({"synced, cursor, created, updated": found})
        self.assertEqual(
            found,
            (True, self.parameters.CHANGE_NUMBER, 1, 1),
            msg=self.parameters.MSG_SYNC_NOW_SETTING,
            abort_on_fail=False,
        )
