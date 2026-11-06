"""
* @file     ${tests/logic/integration_sync_gitlab_hosts.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which host the GitLab sync calls.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the GitLab host choice.
"""

from tests.bloom_test_base import BloomTestCase


class IntegrationSyncGitlabHostsBase(BloomTestCase):

    def bud_configured_base_url_is_called(self):
        hosts = [call.host for call in self.bloom.site.calls]
        self.print_variables({"hosts": hosts})
        self.assertIn(
            member=self.parameters.GITLAB_HOST,
            container=hosts,
            msg=self.parameters.MSG_GITLAB_HOST,
            abort_on_fail=False,
        )

    def bud_gitlab_com_is_called_without_a_base_url(self):
        hosts = [call.host for call in self.bloom.site.calls]
        self.print_variables({"hosts": hosts})
        self.assertIn(
            member=self.parameters.GITLAB_COM,
            container=hosts,
            msg=self.parameters.MSG_GITLAB_HOST,
            abort_on_fail=False,
        )

    def bud_issue_list_of_the_encoded_repository_is_read(self):
        prefix = f"/api/v4/projects/{self.parameters.REPO.replace('/', '%2F')}/issues".encode()
        paths = [call.raw_path for call in self.bloom.site.calls]
        self.print_variables({"paths": paths})
        self.assertTrue(
            all(path.startswith(prefix) for path in paths) and len(paths) == 2,
            msg=self.parameters.MSG_GITLAB_PATH,
            abort_on_fail=False,
        )

    def bud_closed_issues_close_both_defects(self):
        statuses = [
            self.bloom.bloom_get_defect(defect_id).status for defect_id in self.tc_defect_ids
        ]
        self.print_variables({"defects": statuses})
        self.assertEqual(
            statuses,
            [self.parameters.DEFECT_CLOSED, self.parameters.DEFECT_CLOSED],
            msg=self.parameters.MSG_GIT_DEFECT_CLOSED,
            abort_on_fail=False,
        )
