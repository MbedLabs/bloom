"""
* @file     ${tests/api/BLOOM_project_counts_batched.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The project list reports the same counts as each project's detail, per project, with a bounded number of statements.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the project list on the full application as administrator.
"""

from tests.api.project_counts_batched import ProjectCountsBatchedBase


class ProjectCountsBatchedTest(ProjectCountsBatchedBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectCountsBatchedTest().run()
