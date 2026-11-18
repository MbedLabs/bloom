"""
* @file     ${tests/api/BLOOM_projects_delete.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An admin deletes a project, with or without requirements; an anonymous delete is refused.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the project delete route of the full app in-process.
"""

from tests.api.projects_delete import ProjectsDeleteBase


class ProjectsDeleteTest(ProjectsDeleteBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        self.admin, self.login = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        self.plain_id, self.with_requirement_id, self.protected_id = (
            self.bloom.bloom_api_create_project(self.admin, prefix).json().get("id")
            for prefix in self.parameters.DELETE_PREFIXES
        )
        self.requirement = self.bloom.bloom_api_create_requirement(
            self.admin, self.with_requirement_id, self.parameters.DELETE_REQUIREMENT_TITLE
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectsDeleteTest().run()
