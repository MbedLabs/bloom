"""
* @file     ${tests/api/BLOOM_project_policy_grants.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Group-owned policies and explicit project replacements enforce complete rules.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests policies, grants and entries on the full application; each step uses its own project and users.
"""

from tests.api.project_policy_grants import ProjectPolicyGrantsBase


class ProjectPolicyGrantsTest(ProjectPolicyGrantsBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectPolicyGrantsTest().run()
