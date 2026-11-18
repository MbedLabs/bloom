"""
* @file     ${tests/api/BLOOM_project_member_retention.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Removing project access preserves the account and its project contributions.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests removing and restoring an author's assignment on the full application; each case starts from a new database.
"""

from tests.api.project_member_retention import ProjectMemberRetentionBase


class ProjectMemberRetentionTest(ProjectMemberRetentionBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectMemberRetentionTest().run()
