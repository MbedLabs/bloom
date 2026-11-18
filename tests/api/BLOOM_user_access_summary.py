"""
* @file     ${tests/api/BLOOM_user_access_summary.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An Admin reads a user's groups and project access by name only.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the access summary on the full application; each step uses its own user.
"""

from tests.api.user_access_summary import UserAccessSummaryBase


class UserAccessSummaryTest(UserAccessSummaryBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    UserAccessSummaryTest().run()
