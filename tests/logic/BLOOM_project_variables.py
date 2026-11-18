"""
* @file     ${tests/logic/BLOOM_project_variables.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A project variable update writes its fields; a duplicate kind and key is refused.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests an update and a duplicate against a mocked database session.
"""

from tests.logic.project_variables import ProjectVariablesBase


class ProjectVariablesTest(ProjectVariablesBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectVariablesTest().run()
