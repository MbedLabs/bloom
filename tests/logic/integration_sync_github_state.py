"""
* @file     ${tests/logic/integration_sync_github_state.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the GitHub sync of linked defects and change requests.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the GitHub issue state sync.
"""

from datetime import timedelta

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncGithubStateBase(BloomTestCase):

    def bud_issue_list_is_read_on_github_since_creation(self):
        call = self.bloom.site.calls[0]
        since = self.bloom.bloom_git_time(
            self.parameters.NOW
            - self.parameters.SETTING_AGE
            - timedelta(minutes=self.parameters.OVERLAP_MINUTES)
        )
        found = (call.host, call.path, call.params.get("since"))
        self.print_variables({"host, path, since": found})
        self.assertEqual(
            found,
            (self.parameters.GITHUB_API, f"/repos/{self.parameters.REPO}/issues", since),
            msg=self.parameters.MSG_GITHUB_CALL,
            abort_on_fail=False,
        )

    def bud_defect_of_a_closed_issue_is_closed(self):
        defect = self.bloom.bloom_get_defect(self.tc_defect_id)
        found = (defect.external_issue_state, defect.status)
        self.print_variables({"issue state, status": found})
        self.assertEqual(
            found,
            (self.parameters.GIT_CLOSED, self.parameters.DEFECT_CLOSED),
            msg=self.parameters.MSG_GIT_DEFECT_CLOSED,
            abort_on_fail=False,
        )

    def bud_change_request_takes_the_state_and_keeps_its_status(self):
        change = self.bloom.bloom_get_change(self.tc_change_id)
        found = (change.external_issue_state, change.status)
        self.print_variables({"issue state, status": found})
        self.assertEqual(
            found,
            (self.parameters.GIT_CLOSED, self.parameters.CHANGE_SUBMITTED),
            msg=self.parameters.MSG_GIT_CHANGE_STATE_ONLY,
            abort_on_fail=False,
        )

    def bud_run_counts_two_updates_and_ignores_the_pull_request(self):
        setting = self.bloom.bloom_get_setting(self.tc_setting_id)
        found = (setting.sync_updated, setting.synced_at)
        self.print_variables({"updated, synced at": found})
        self.assertEqual(
            found, (2, self.parameters.NOW), msg=self.parameters.MSG_GIT_COUNTS, abort_on_fail=False
        )
