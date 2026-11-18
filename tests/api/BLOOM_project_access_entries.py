"""
* @file     ${tests/api/BLOOM_project_access_entries.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Direct user entries use selected policies or a project-specific Owner grant.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the member routes on the full application; each step uses its own project and user.
"""

from tests.api.project_access_entries import ProjectAccessEntriesBase


class ProjectAccessEntriesTest(ProjectAccessEntriesBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectAccessEntriesTest().run()
