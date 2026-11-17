"""
* @file     ${tests/logic/BLOOM_requirement_text.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Editor text becomes a plain description; ReqIF import and project copy store no editor content.
* @author   Amine El Omari
* @date     2026-11-14
* @version  1.0.0
* @note     This module tests the converter, the ReqIF import and the project copy of requirements.
"""

from tests.logic.requirement_text import RequirementTextBase


class RequirementTextTest(RequirementTextBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        parameters = self.parameters
        bloom.bloom_add_user(parameters.TEXT_ADMIN, bloom.bloom_role(parameters.TEXT_ADMIN_ROLE))

        self.project_id = bloom.bloom_create_project(parameters.TEXT_PREFIX)
        result = bloom.bloom_import_reqif(self.project_id, parameters.REQIF_SAMPLE)
        self.import_counts = (
            result.imported,
            result.links_created,
            result.specifications,
            result.new_ids,
        )
        self.imported = bloom.bloom_requirement_rows(parameters.REQIF_FIELDS, self.project_id)

        self.source_id, self.target_id = (
            bloom.bloom_create_project(prefix) for prefix in parameters.TEXT_COPY_PREFIXES
        )
        bloom.bloom_add_artefact("REQ", project_id=self.source_id, **parameters.TEXT_COPY_SOURCE)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementTextTest().run()
