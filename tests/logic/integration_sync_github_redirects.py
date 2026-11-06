"""
* @file     ${tests/logic/integration_sync_github_redirects.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which GitHub redirects the sync follows.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of GitHub redirects.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncGithubRedirectsBase(BloomTestCase):

    def bud_moved_repository_defect_is_closed(self):
        self.print_variables({"defect": self.tc_first_status})
        self.assertEqual(
            self.tc_first_status,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_GIT_DEFECT_CLOSED,
            abort_on_fail=False,
        )

    def bud_redirect_on_github_api_is_followed(self):
        self.print_variables({"followed": self.tc_followed})
        self.assertEqual(
            self.tc_followed,
            self.parameters.REDIRECTED,
            msg=self.parameters.MSG_REDIRECT_FOLLOWED,
            abort_on_fail=False,
        )

    def bud_redirect_to_another_host_is_not_followed(self):
        self.print_variables({"calls of the second run": self.tc_second_calls})
        self.assertEqual(
            self.tc_second_calls,
            1,
            msg=self.parameters.MSG_FOREIGN_NOT_FOLLOWED,
            abort_on_fail=False,
        )

    def bud_run_error_names_the_redirect(self):
        error = self.bloom.bloom_get_setting(self.tc_setting_id).sync_error
        self.print_variables({"error": error})
        self.assertEqual(
            error,
            self.parameters.LIST_ERROR.format(tracker="GitHub", status=self.parameters.MOVED),
            msg=self.parameters.MSG_REDIRECT_ERROR,
            abort_on_fail=False,
        )
