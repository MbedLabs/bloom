"""
* @file     ${tests/sec/BLOOM_traceability_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader's traceability, coverage and impact hold customer artefacts only.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the traceability API with one external reader, a verified customer requirement and a verified internal one.
"""

from tests.sec.traceability_external_visibility import (
    TraceabilityExternalVisibilityBase,
)


class TraceabilityExternalVisibilityTest(TraceabilityExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        reader = bloom.bloom_create_external_reader_environment(
            bloom.bloom_default_external_doc_types()
        )
        project, status = reader.project_id, values.STATUS_APPROVED
        internal_requirement = None
        pairs = (
            (values.READER_CUSTOMER_REQ, values.READER_CUSTOMER_TC, values.CUSTOMER_VISIBILITY),
            (values.READER_INTERNAL_REQ, values.READER_INTERNAL_TC, values.INTERNAL_VISIBILITY),
        )
        for req_id, tc_id, visibility in pairs:
            internal_requirement = bloom.bloom_add_requirement(project, req_id, visibility)
            test_case = bloom.bloom_add_test_case(
                project, tc_id, tc_id, status=status, visibility=visibility
            )
            bloom.bloom_add_artefact_link(project, test_case, internal_requirement)
        self.matrix = bloom.bloom_api_traceability(reader.headers, project)
        self.coverage = bloom.bloom_api_coverage_gaps(reader.headers, project)
        self.impact = bloom.bloom_api_impact(reader.headers, internal_requirement)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TraceabilityExternalVisibilityTest().run()
