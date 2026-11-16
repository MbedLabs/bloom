"""
* @file     ${tests/sec/BLOOM_external_visibility_direct_apis.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A customer requirement, test case and campaign show an external reader their customer neighbours only.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests three detail APIs with one external reader and customer artefacts linked to internal ones.
"""

from tests.sec.external_visibility_direct_apis import ExternalVisibilityDirectApisBase


class ExternalVisibilityDirectApisTest(ExternalVisibilityDirectApisBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        reader = bloom.bloom_create_external_reader_environment(doc_types=None)
        project, status = reader.project_id, values.STATUS_APPROVED
        customer, internal = values.CUSTOMER_VISIBILITY, values.INTERNAL_VISIBILITY
        pending = values.READER_CAMPAIGN_PENDING
        root = bloom.bloom_add_requirement(project, values.READER_CUSTOMER_REQ, customer)
        hidden_req = bloom.bloom_add_requirement(project, values.READER_INTERNAL_REQ, internal)
        visible_tc = bloom.bloom_add_test_case(
            project,
            values.READER_CUSTOMER_TC,
            values.READER_CUSTOMER_TC,
            status=status,
            visibility=customer,
        )
        hidden_tc = bloom.bloom_add_test_case(
            project,
            values.READER_INTERNAL_TC,
            values.READER_INTERNAL_TC,
            status=status,
            visibility=internal,
        )
        visible_suite = bloom.bloom_add_test_suite(
            project, values.READER_VISIBLE_SUITE, customer, [visible_tc]
        )
        hidden_suite = bloom.bloom_add_test_suite(
            project, values.READER_HIDDEN_SUITE, internal, [visible_tc, hidden_tc]
        )
        bloom.bloom_add_campaign(
            project,
            values.READER_VISIBLE_CAMPAIGN,
            customer,
            [visible_suite],
            [(visible_tc, pending)],
        )
        bloom.bloom_add_campaign(
            project,
            values.READER_HIDDEN_CAMPAIGN,
            internal,
            [hidden_suite],
            [(visible_tc, pending), (hidden_tc, pending)],
        )
        bloom.bloom_add_artefact_link(project, visible_tc, root)
        bloom.bloom_add_artefact_link(project, visible_tc, hidden_req)
        bloom.bloom_add_artefact_link(project, hidden_tc, root)
        self.requirement = bloom.bloom_api_read_requirement(reader.headers, root)
        self.test_case = bloom.bloom_api_get_test_case(reader.headers, visible_tc)
        self.campaign = bloom.bloom_api_get_campaign(reader.headers, values.READER_VISIBLE_CAMPAIGN)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExternalVisibilityDirectApisTest().run()
