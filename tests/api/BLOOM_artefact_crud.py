"""
* @file     ${tests/api/BLOOM_artefact_crud.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    CRUD across the controlled artefacts: defects, changes, risks, baselines and project members.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the routes on the full application as administrator in one project.
"""

from tests.api.artefact_crud import ArtefactCrudBase


class ArtefactCrudTest(ArtefactCrudBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.project = self.bloom.bloom_api_new_project(self.admin, self.parameters.CRUD_PREFIX)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactCrudTest().run()
