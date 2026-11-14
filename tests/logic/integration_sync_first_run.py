"""
* @file     ${tests/logic/integration_sync_first_run.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the first scheduled Jira sync of an integration.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the first Jira sync.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncFirstRunBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_due_setting_is_synced(self):
        self.print_variables({"synced": self.tc_synced, "setting": self.tc_setting_id})
        self.assertEqual(
            self.tc_synced,
            [self.tc_setting_id],
            msg=self.parameters.MSG_SETTING_SYNCED,
            abort_on_fail=False,
        )

    def bud_creation_search_asks_for_open_bugs(self):
        creation = [q for q in self.bloom.site.jql if self.parameters.CREATION_MARK in q]
        self.print_variables({"creation search": creation})
        self.assertEqual(
            creation,
            [self.parameters.CREATION_JQL.format(project=self.parameters.JIRA_PROJECT)],
            msg=self.parameters.MSG_CREATION_SEARCH_OPEN_BUGS,
            abort_on_fail=False,
        )

    def bud_new_bug_becomes_one_defect(self):
        new = self.bloom.bloom_list_defects_linked_to(self.parameters.NEW_NUMBER)
        self.print_variables({"defects of the new bug": len(new)})
        self.assertEqual(
            len(new), 1, msg=self.parameters.MSG_NEW_BUG_ONE_DEFECT, abort_on_fail=False
        )

    def bud_linked_issue_and_task_create_no_defect(self):
        count = self.bloom.bloom_count_defects()
        self.print_variables({"defects": count})
        self.assertEqual(
            count, 2, msg=self.parameters.MSG_NO_TASK_NO_DUPLICATE, abort_on_fail=False
        )

    def bud_new_defect_takes_summary_project_and_open_status(self):
        new = self.bloom.bloom_list_defects_linked_to(self.parameters.NEW_NUMBER)
        found = [(d.title, d.project_id, d.status) for d in new]
        self.print_variables({"new defect": found})
        self.assertEqual(
            found,
            [(self.parameters.NEW_SUMMARY, self.tc_project_id, self.parameters.DEFECT_OPEN)],
            msg=self.parameters.MSG_NEW_DEFECT_CONTENT,
            abort_on_fail=False,
        )

    def bud_full_scan_is_cleared(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.print_variables({"full scan": setting.sync_full_scan})
        self.assertEqual(
            setting.sync_full_scan,
            False,
            msg=self.parameters.MSG_FULL_SCAN_CLEARED,
            abort_on_fail=False,
        )

    def bud_run_is_stamped_at_now(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        self.print_variables(
            {"synced at": setting.synced_at, "checked at": setting.sync_checked_at}
        )
        self.assertEqual(
            (setting.synced_at, setting.sync_checked_at),
            (self.parameters.NOW, self.parameters.NOW),
            msg=self.parameters.MSG_RUN_STAMPED,
            abort_on_fail=False,
        )

    def bud_run_counts_one_created_and_no_error(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        counts = (setting.sync_created, setting.sync_updated, setting.sync_error)
        self.print_variables({"created, updated, error": counts})
        self.assertEqual(
            counts, (1, 0, None), msg=self.parameters.MSG_RUN_COUNTS, abort_on_fail=False
        )

    def bud_new_defect_logs_the_issue_it_came_from(self):
        new = self.bloom.bloom_list_defects_linked_to(self.parameters.NEW_NUMBER)
        ids = {d.id for d in new}
        events = [
            (e.event_type, e.payload_summary)
            for e in self.bloom.bloom_list_defect_events()
            if e.defect_id in ids
        ]
        self.print_variables({"events": events})
        self.assertEqual(
            events,
            [
                (
                    self.parameters.SYNCED_EVENT,
                    self.parameters.CREATED_FROM.format(
                        key=self.bloom.bloom_jira_key(self.parameters.NEW_NUMBER)
                    ),
                )
            ],
            msg=self.parameters.MSG_ORIGIN_LOGGED,
            abort_on_fail=False,
        )
