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
        values = self.parameters
        at_boundary, below, other_type = values.WIDENING_PREFIXES
        self.at_boundary = self.bloom.bloom_create_project(at_boundary)
        self.bloom.bloom_add_requirements(self.at_boundary, values.WIDENING_AT_BOUNDARY)
        self.below = self.bloom.bloom_create_project(below)
        self.bloom.bloom_add_requirements(self.below, values.WIDENING_BELOW)
        self.other_type = self.bloom.bloom_create_project(other_type)
        self.bloom.bloom_add_requirements(self.other_type, values.WIDENING_OTHER_TYPE)
        self.bloom.bloom_add_test_case(
            self.other_type, values.WIDENING_TEST_CASE, values.WIDENING_TEST_CASE
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IdWideningTest().run()
