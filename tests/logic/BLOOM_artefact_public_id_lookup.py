"""
* @file     ${tests/logic/BLOOM_artefact_public_id_lookup.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Artefacts are found by public id as well as database id, with the same backlinks.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests a project with a requirement, a test case and a linked defect.
"""

from tests.logic.artefact_public_id_lookup import ArtefactPublicIdLookupBase


class ArtefactPublicIdLookupTest(ArtefactPublicIdLookupBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        project_id = bloom.bloom_create_project(self.parameters.LOOKUP_PREFIX)
        requirement, test_case, defect_kind = self.parameters.LOOKUP_KINDS
        bloom.bloom_add_user(
            self.parameters.LOOKUP_ADMIN, bloom.bloom_role(self.parameters.LOOKUP_ADMIN_ROLE)
        )
        requirement_id = bloom.bloom_add_artefact(
            requirement, project_id=project_id, **self.parameters.LOOKUP_REQUIREMENT
        )
        self.test_case_id = bloom.bloom_add_artefact(
            test_case, project_id=project_id, **self.parameters.LOOKUP_TEST_CASE
        )
        self.defect_id = bloom.bloom_add_artefact(
            defect_kind, project_id=project_id, **self.parameters.LOOKUP_DEFECT
        )
        bloom.bloom_add_link(
            project_id,
            (defect_kind, self.defect_id),
            (requirement, requirement_id),
            self.parameters.LOOKUP_ROLE,
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactPublicIdLookupTest().run()
