"""
* @file     ${tests/logic/BLOOM_project_naming.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Project prefixes follow the id convention; artefact ids are never set by clients.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests project create and update schemas and seven artefact creates.
"""

from tests.logic.project_naming import ProjectNamingBase


class ProjectNamingTest(ProjectNamingBase):

    def setUpClass(self):
        super().setUpClass()
        self.fields = {
            schema: self.bloom.bloom_schema_fields(schema)
            for schema in ["RequirementCreate", "TestCaseCreate", "DocumentCreate"]
            + list(self.parameters.NAMING_OTHERS)
        }

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectNamingTest().run()
