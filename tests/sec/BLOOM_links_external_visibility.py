"""
* @file     ${tests/sec/BLOOM_links_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader lists a link only when both of its ends are customer artefacts.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the link API with one external reader and three links, two of them with an internal end.
"""

from tests.sec.links_external_visibility import LinksExternalVisibilityBase


class LinksExternalVisibilityTest(LinksExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        self.reader = bloom.bloom_create_external_reader_environment(
            bloom.bloom_default_external_doc_types()
        )
        project, status = self.reader.project_id, values.STATUS_APPROVED
        customer, internal = values.CUSTOMER_VISIBILITY, values.INTERNAL_VISIBILITY
        customer_req = bloom.bloom_add_requirement(project, values.READER_CUSTOMER_REQ, customer)
        internal_req = bloom.bloom_add_requirement(project, values.READER_INTERNAL_REQ, internal)
        customer_tc = bloom.bloom_add_test_case(
            project,
            values.READER_CUSTOMER_TC,
            values.READER_CUSTOMER_TC,
            status=status,
            visibility=customer,
        )
        internal_tc = bloom.bloom_add_test_case(
            project,
            values.READER_INTERNAL_TC,
            values.READER_INTERNAL_TC,
            status=status,
            visibility=internal,
        )
        bloom.bloom_add_artefact_link(project, customer_tc, customer_req)
        bloom.bloom_add_artefact_link(project, customer_tc, internal_req)
        bloom.bloom_add_artefact_link(project, internal_tc, customer_req)
        self.customer_ends = (customer_tc, customer_req)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    LinksExternalVisibilityTest().run()
