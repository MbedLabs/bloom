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
        name = self.parameters.NAMING_PROJECT["name"]
        try_schema = self.bloom.bloom_try_schema
        self.tc_project = try_schema("ProjectCreate", self.parameters.NAMING_PROJECT)
        self.tc_bad_prefixes = {
            prefix: try_schema("ProjectCreate", {"name": name, "prefix": prefix}).error
            for prefix in self.parameters.NAMING_BAD_PREFIXES
        }
        self.tc_bad_update = try_schema("ProjectUpdate", self.parameters.NAMING_BAD_UPDATE)
        self.tc_requirement = try_schema("RequirementCreate", self.parameters.NAMING_REQUIREMENT)
        self.tc_test_case = try_schema("TestCaseCreate", self.parameters.NAMING_TEST_CASE)
        self.tc_document = try_schema("DocumentCreate", self.parameters.NAMING_DOCUMENT)
        self.tc_others = {
            schema: try_schema(schema, body)
            for schema, (_, body) in self.parameters.NAMING_OTHERS.items()
        }
        self.tc_fields = {
            schema: self.bloom.bloom_schema_fields(schema)
            for schema in ["RequirementCreate", "TestCaseCreate", "DocumentCreate"]
            + list(self.parameters.NAMING_OTHERS)
        }

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectNamingTest().run()
