"""
* @file     ${tests/logic/integration_sync_later_run.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a later scheduled Jira sync of an integration that synced before.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of a later Jira sync.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncLaterRunBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_searches_cover_the_time_since_the_last_sync(self):
        window = self.parameters.LAST_SYNC_MINUTES + self.parameters.OVERLAP_MINUTES
        self.print_variables({"searches": self.bloom.site.jql, "window": window})
        self.assertEqual(
            self.bloom.site.jql,
            [
                self.parameters.WINDOW_CREATION_JQL.format(
                    project=self.parameters.JIRA_PROJECT, minutes=window
                ),
                self.parameters.WINDOW_CHANGED_JQL.format(
                    project=self.parameters.JIRA_PROJECT, minutes=window
                ),
            ],
            msg=self.parameters.MSG_WINDOW,
            abort_on_fail=False,
        )

    def bud_defect_takes_the_jira_changes(self):
        defect = self.bloom.bloom_get_defect(self.tc_defect_id)
        found = (
            defect.status,
            defect.title,
            defect.priority,
            defect.description,
            defect.external_issue_state,
        )
        self.print_variables({"defect": found})
        self.assertEqual(
            found,
            (
                self.parameters.DEFECT_CLOSED,
                self.parameters.CHANGED_TITLE,
                self.parameters.BLOOM_PRIORITY,
                self.parameters.CHANGED_DESCRIPTION,
                self.parameters.JIRA_DONE,
            ),
            msg=self.parameters.MSG_DEFECT_FOLLOWS,
            abort_on_fail=False,
        )

    def bud_change_request_is_closed(self):
        status = self.bloom.bloom_get_change(self.tc_change_id).status
        self.print_variables({"change request": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_CHANGE_CLOSED,
            abort_on_fail=False,
        )

    def bud_run_counts_two_updates(self):
        updated = self.bloom.bloom_get_setting(self.tc_setting_id).sync_updated
        self.print_variables({"updated": updated})
        self.assertEqual(updated, 2, msg=self.parameters.MSG_TWO_UPDATES, abort_on_fail=False)

    def bud_defect_logs_one_sync(self):
        events = [e.event_type for e in self.bloom.bloom_list_defect_events()]
        self.print_variables({"defect events": events})
        self.assertEqual(
            events,
            [self.parameters.SYNCED_EVENT],
            msg=self.parameters.MSG_ONE_SYNC_EVENT,
            abort_on_fail=False,
        )

    def bud_change_request_logs_one_sync(self):
        events = [e.event_type for e in self.bloom.bloom_list_change_events()]
        self.print_variables({"change request events": events})
        self.assertEqual(
            events,
            [self.parameters.SYNCED_EVENT],
            msg=self.parameters.MSG_ONE_SYNC_EVENT,
            abort_on_fail=False,
        )
