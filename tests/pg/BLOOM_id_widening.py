"""
* @file     ${tests/pg/BLOOM_id_widening.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Passing 999 rewrites the stored ids of that project and type and leaves other rows alone.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests next_doc_id on three projects: at the boundary, below it, and with a second artefact type.
"""

from tests.pg.id_widening import IdWideningBase


class IdWideningTest(IdWideningBase):

    def setUpClass(self):
        super().setUpClass()
        at_boundary, below, other_type = self.parameters.WIDENING_PREFIXES
        project = self.bloom.bloom_create_project(at_boundary)
        self.bloom.bloom_add_requirements(project, self.parameters.WIDENING_AT_BOUNDARY)
        self.next_at_boundary = self.bloom.bloom_next_requirement_id(project, at_boundary)
        self.stored_at_boundary = self.bloom.bloom_list_requirement_ids(project)
        project = self.bloom.bloom_create_project(below)
        self.bloom.bloom_add_requirements(project, self.parameters.WIDENING_BELOW)
        self.next_below = self.bloom.bloom_next_requirement_id(project, below)
        self.stored_below = self.bloom.bloom_list_requirement_ids(project)
        project = self.bloom.bloom_create_project(other_type)
        self.bloom.bloom_add_requirements(project, self.parameters.WIDENING_OTHER_TYPE)
        test_case = self.parameters.WIDENING_TEST_CASE
        self.bloom.bloom_add_test_case(project, test_case, test_case)
        self.bloom.bloom_next_requirement_id(project, other_type)
        self.test_case_ids = self.bloom.bloom_list_test_case_ids()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IdWideningTest().run()
