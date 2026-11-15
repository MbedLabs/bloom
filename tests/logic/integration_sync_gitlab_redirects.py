"""
* @file     ${tests/logic/integration_sync_gitlab_redirects.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that the GitLab sync follows no redirect.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of GitLab redirects.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncGitlabRedirectsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_only_the_configured_gitlab_host_is_called(self):
        hosts = [call.host for call in self.bloom.site.calls]
        self.print_variables({"hosts": hosts})
        self.assertEqual(
            hosts,
            [self.parameters.GITLAB_HOST],
            msg=self.parameters.MSG_GITLAB_ONLY_HOST,
            abort_on_fail=False,
        )

    def bud_run_error_names_the_redirect(self):
        error = self.bloom.bloom_get_setting(self.tc_setting_id).sync_error
        self.print_variables({"error": error})
        self.assertEqual(
            error,
            self.parameters.LIST_ERROR.format(tracker="GitLab", status=self.parameters.MOVED),
            msg=self.parameters.MSG_REDIRECT_ERROR,
            abort_on_fail=False,
        )
