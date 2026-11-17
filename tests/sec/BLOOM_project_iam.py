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

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectIamTest().run()
