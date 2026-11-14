"""
* @file     ${tests/sec/BLOOM_project_iam.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Admins enter any project; others need access and a term granting the action.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests an admin, an unassigned user and a missing and granted action.
"""

from tests.sec.project_iam import ProjectIamBase


class ProjectIamTest(ProjectIamBase):

    def setUpClass(self):
        super().setUpClass()
        edit = self.parameters.IAM_EDIT_REQUIREMENT
        self.tc_admin = self.bloom.bloom_require_project_access(self.parameters.IAM_ADMIN)
        self.tc_unassigned = self.bloom.bloom_require_project_access(self.parameters.IAM_MAINTAINER)
        self.tc_missing = self.bloom.bloom_require_project_access(
            self.parameters.IAM_MAINTAINER, self.parameters.IAM_VIEW_ONLY, edit
        )
        self.tc_granted = self.bloom.bloom_require_project_access(
            self.parameters.IAM_MAINTAINER, self.parameters.IAM_VIEW_AND_EDIT, edit
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectIamTest().run()
