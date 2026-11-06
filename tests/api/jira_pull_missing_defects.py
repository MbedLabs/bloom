"""
* @file     ${tests/api/jira_pull_missing_defects.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests Sync now pulling the missing defects page by page.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests Sync now pulling the missing defects page by page.
"""

from tests.bloom_test_base import BloomTestCase


class JiraPullMissingDefectsBase(BloomTestCase):

    def bud_pull_counts_what_it_saw(self):
        found = (
            self.tc_result.searched,
            self.tc_result.created,
            self.tc_result.already_linked,
            self.tc_result.skipped,
        )
        self.print_variables({"searched, created, already linked, skipped": found})
        self.assertEqual(
            found,
            self.parameters.PULL_COUNTS,
            msg=self.parameters.MSG_PULL_COUNTS,
            abort_on_fail=False,
        )
        self.assertEqual(
            (self.tc_result.updated, self.tc_result.removed),
            self.parameters.PULL_UNCHANGED,
            msg=self.parameters.MSG_PULL_COUNTS,
            abort_on_fail=False,
        )

    def bud_pull_names_the_new_defect(self):
        pulled = [
            d.defect_id
            for d in self.bloom.bloom_list_defects_linked_to(self.parameters.PULL_NEW_NUMBER)
        ]
        self.print_variables({"new ids": self.tc_result.new_ids, "pulled": pulled})
        self.assertEqual(
            self.tc_result.new_ids, pulled, msg=self.parameters.MSG_PULL_NEW_ID, abort_on_fail=False
        )

    def bud_pull_asks_for_open_bugs_and_follows_the_next_page(self):
        found = (self.tc_seen[0]["jql"], self.tc_seen[1].get("nextPageToken"))
        self.print_variables({"first search, second token": found})
        self.assertEqual(
            found,
            (
                self.parameters.CREATION_JQL.format(project=self.parameters.JIRA_PROJECT),
                self.parameters.NEXT_PAGE_TOKEN,
            ),
            msg=self.parameters.MSG_PULL_SEARCHES,
            abort_on_fail=False,
        )

    def bud_pulled_defect_logs_it_was_pulled(self):
        ids = {
            d.id for d in self.bloom.bloom_list_defects_linked_to(self.parameters.PULL_NEW_NUMBER)
        }
        events = [e.event_type for e in self.bloom.bloom_list_defect_events() if e.defect_id in ids]
        self.print_variables({"events": events})
        self.assertEqual(
            events,
            [self.parameters.PULLED_EVENT],
            msg=self.parameters.MSG_PULL_EVENT,
            abort_on_fail=False,
        )
