"""
* @file     ${tests/api/BLOOM_projects_delete.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An admin deletes a project, with or without requirements; an anonymous delete is refused.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the project delete route of the full app in-process.
"""

from types import SimpleNamespace

from tests.api.projects_delete import ProjectsDeleteBase


class ProjectsDeleteTest(ProjectsDeleteBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, self.tc_login = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        plain, with_requirement, protected = (
            self.bloom.bloom_api_create_project(admin, prefix).json().get("id")
            for prefix in self.parameters.DELETE_PREFIXES
        )
        requirement = self.bloom.bloom_api_create_requirement(
            admin, with_requirement, self.parameters.DELETE_REQUIREMENT_TITLE
        )
        self.tc_plain = self._delete(admin, plain)
        self.tc_with_requirement = self._delete(admin, with_requirement)
        self.tc_with_requirement.requirement = requirement.status_code
        self.tc_anonymous = self.bloom.bloom_api_delete_project(None, protected).status_code

    def tearDownClass(self):
        super().tearDownClass()

    def _delete(self, headers, project_id):
        """Delete the project and read it back, returning both answers' status codes."""
        delete = self.bloom.bloom_api_delete_project(headers, project_id)
        read = self.bloom.bloom_api_get_project(headers, project_id)
        return SimpleNamespace(delete=delete.status_code, read=read.status_code)


if __name__ == "__main__":
    ProjectsDeleteTest().run()
