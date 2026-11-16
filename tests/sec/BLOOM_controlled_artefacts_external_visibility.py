"""
* @file     ${tests/sec/BLOOM_controlled_artefacts_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader gets customer designs, risks, changes, test concepts and defects only.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests five artefact APIs with one external reader and a customer and an internal artefact of each kind.
"""

from tests.sec.controlled_artefacts_external_visibility import (
    ControlledArtefactsExternalVisibilityBase,
)


class ControlledArtefactsExternalVisibilityTest(ControlledArtefactsExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        reader = bloom.bloom_create_external_reader_environment(doc_types=None)
        self.tc_pairs = [
            bloom.bloom_add_controlled_pair(reader.project_id, kind, code)
            for kind, _, _, code in self.parameters.CONTROLLED_KINDS
        ]
        self.tc_seen = [
            bloom.bloom_api_probe_controlled(reader.headers, reader.project_id, path, pair)
            for (_, path, _, _), pair in zip(self.parameters.CONTROLLED_KINDS, self.tc_pairs)
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ControlledArtefactsExternalVisibilityTest().run()
