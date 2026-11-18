"""
* @file     ${tests/api/BLOOM_project_bundle_assignments.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Project bundle assignments and application grants keep their scopes separate.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests bundles, project entries and application policies on the full application with the built-in catalogue.
"""

from tests.api.project_bundle_assignments import ProjectBundleAssignmentsBase


class ProjectBundleAssignmentsTest(ProjectBundleAssignmentsBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.bloom.bloom_seed_default_catalogue()
        self.bloom.bloom_enforce_foreign_keys()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectBundleAssignmentsTest().run()
