"""
* @file     ${tests/sec/BLOOM_artefacts_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader gets the related artefacts of a customer requirement and a 404 for an internal one.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the related-artefacts API with one external reader, one customer and one internal requirement.
"""

from tests.sec.artefacts_external_visibility import ArtefactsExternalVisibilityBase


class ArtefactsExternalVisibilityTest(ArtefactsExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        reader = bloom.bloom_create_external_reader_environment(
            bloom.bloom_default_external_doc_types()
        )
        customer = bloom.bloom_add_requirement(
            reader.project_id, values.READER_CUSTOMER_REQ, values.CUSTOMER_VISIBILITY
        )
        internal = bloom.bloom_add_requirement(
            reader.project_id, values.READER_INTERNAL_REQ, values.INTERNAL_VISIBILITY
        )
        kind = values.READER_REQUIREMENT_KIND
        self.tc_hidden = bloom.bloom_api_related(reader.headers, kind, internal)
        self.tc_visible = bloom.bloom_api_related(reader.headers, kind, customer)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactsExternalVisibilityTest().run()
