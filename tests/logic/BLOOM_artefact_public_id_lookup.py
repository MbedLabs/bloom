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
        self.tc_test_case_id = bloom.bloom_add_artefact(
            test_case, project_id=project_id, **self.parameters.LOOKUP_TEST_CASE
        )
        defect_id = bloom.bloom_add_artefact(
            defect_kind, project_id=project_id, **self.parameters.LOOKUP_DEFECT
        )
        bloom.bloom_add_link(
            project_id,
            (defect_kind, defect_id),
            (requirement, requirement_id),
            self.parameters.LOOKUP_ROLE,
        )
        kind, field = self.parameters.LOOKUP_TEST_CASE_TYPE, self.parameters.LOOKUP_TEST_CASE_FIELD
        self.tc_by_public = bloom.bloom_lookup_artefact(
            kind, self.parameters.LOOKUP_TEST_CASE["tc_id"], field
        )
        self.tc_by_database = bloom.bloom_lookup_artefact(kind, str(self.tc_test_case_id), field)
        self.tc_unknown = bloom.bloom_lookup_artefact(kind, self.parameters.LOOKUP_UNKNOWN, field)
        defect = self.parameters.LOOKUP_DEFECT_TYPE
        self.tc_related_public = bloom.bloom_related_artefacts(
            defect, self.parameters.LOOKUP_DEFECT["defect_id"]
        )
        self.tc_related_database = bloom.bloom_related_artefacts(defect, str(defect_id))

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactPublicIdLookupTest().run()
