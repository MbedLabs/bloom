"""
* @file     ${tests/api/BLOOM_jira_pull_errors.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Sync now reports what it needs and Jira's errors.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests Sync now without a project key, for an unknown integration, refused and unreachable.
"""

from tests.api.jira_pull_errors import JiraPullErrorsBase


class JiraPullErrorsTest(JiraPullErrorsBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraPullErrorsTest().run()
